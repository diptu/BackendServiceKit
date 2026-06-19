from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.config import settings
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.core.rbac import DEFAULT_ROLE
from app.core.security import (
    create_access_token,
    hash_password,
    password_matches_identifier,
    verify_password,
)
from app.core.token_blacklist import TokenBlacklist, get_token_blacklist
from app.models.role import Role
from app.models.user import ACTIVE_REFRESH_TOKENS, User
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.user import TokenMatrixResponse, UserCreate, UserOut

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired refresh token.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes from DateTime(timezone=True); Postgres
    doesn't. Normalize before comparing against an aware `datetime.now(UTC)`
    (same pattern as `PasswordResetToken.is_valid`)."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        audit_logger: AuditLogger | None = None,
        rate_limiter: RateLimiter | None = None,
        token_blacklist: TokenBlacklist | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.role_repository = role_repository
        self._audit = audit_logger
        self._rate_limiter = rate_limiter or get_rate_limiter()
        self._token_blacklist = token_blacklist or get_token_blacklist()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_token_pair(
        self, user: User, roles: list[str], permissions: list[str]
    ) -> tuple[str, str, str, str]:
        """Return (access_token, refresh_token, access_jti, refresh_jti)."""
        now = datetime.now(UTC)
        access_jti = str(uuid4())
        refresh_jti = str(uuid4())

        # Float, not int(...) — truncating to whole seconds collides with
        # `password_changed_at`'s sub-second precision when a token is
        # issued in the same wall-clock second as a password change,
        # producing false positives/negatives in the invalidate-before
        # comparison in app.core.token_blacklist.is_token_revoked.
        iat = now.timestamp()
        access_claims: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
            "jti": access_jti,
            "iat": iat,
            "roles": roles,
            "permissions": permissions,
            "type": "access",
        }
        refresh_claims: dict[str, Any] = {
            "sub": str(user.id),
            "jti": refresh_jti,
            "iat": iat,
            "roles": roles,
            "permissions": permissions,
            "type": "refresh",
        }

        access_token = create_access_token(
            data=access_claims,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_access_token(
            data=refresh_claims,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        ACTIVE_REFRESH_TOKENS[refresh_jti] = {
            "user_id": str(user.id),
            "revoked": False,
            "expires_at": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        }

        return access_token, refresh_token, access_jti, refresh_jti

    @staticmethod
    def _collect_claims(user: User) -> tuple[list[str], list[str]]:
        roles = [role.slug for role in user.roles]
        # slug (e.g. "users:create"), not the display name — the stable,
        # machine-checkable form route-level permission dependencies match on.
        permissions = list({p.slug for role in user.roles for p in role.permissions})
        return roles, permissions

    async def _record_failed_login(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        """
        Increment the failure counter and, once the threshold is crossed,
        lock the account for an exponentially growing window (capped):
        BASE * 2**(N - THRESHOLD), e.g. 30s/60s/120s/.../900s.
        """
        user.failed_login_count += 1
        newly_locked = False
        if user.failed_login_count >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
            lockout_seconds = min(
                settings.ACCOUNT_LOCKOUT_BASE_SECONDS
                * 2 ** (user.failed_login_count - settings.ACCOUNT_LOCKOUT_THRESHOLD),
                settings.ACCOUNT_LOCKOUT_MAX_SECONDS,
            )
            user.locked_until = datetime.now(UTC) + timedelta(seconds=lockout_seconds)
            newly_locked = True

        await self.user_repository.save(user)

        if newly_locked and self._audit:
            self._audit.log(
                AuditEventType.ACCOUNT_LOCKED,
                email=user.email,
                user_id=str(user.id),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "locked_until": user.locked_until.isoformat()
                    if user.locked_until
                    else None,
                    "failed_login_count": user.failed_login_count,
                },
            )

    # ------------------------------------------------------------------
    # Issue tokens (shared by native login and OAuth callback)
    # ------------------------------------------------------------------

    def issue_tokens(self, user: User) -> TokenMatrixResponse:
        """
        Mint a fresh JWT access + refresh pair for *user* and return
        a TokenMatrixResponse.  Called after any successful authentication
        method (password or OAuth) so the token lifecycle is centralised.
        """
        roles, permissions = self._collect_claims(user)
        access_token, refresh_token, *_ = self._build_token_pair(
            user, roles, permissions
        )
        return TokenMatrixResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            user=UserOut.model_validate(user),
        )

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    async def register(self, payload: UserCreate) -> User:
        email = payload.email.strip().lower()

        if password_matches_identifier(payload.password, email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not match your email address.",
            )

        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )

        default_role = await self.role_repository.get_by_slug(DEFAULT_ROLE.value)

        if not default_role:
            default_role = Role(
                slug=DEFAULT_ROLE.value,
                name=DEFAULT_ROLE.value.replace("_", " ").title(),
                is_system=True,
            )

        if not default_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default role not found.",
            )

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            is_active=True,
            is_verified=False,
            is_superuser=False,
            roles=[default_role],
        )

        return await self.user_repository.create(user)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenMatrixResponse:
        email = email.strip().lower()

        rate_result = await self._rate_limiter.hit(
            f"login:{email}",
            limit=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
            window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )
        if not rate_result.allowed:
            if self._audit:
                self._audit.log(
                    AuditEventType.RATE_LIMIT_EXCEEDED,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Login rate limit exceeded.",
                )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
                headers={"Retry-After": str(rate_result.retry_after_seconds)},
            )

        user = await self.user_repository.get_by_email(email)

        now = datetime.now(UTC)
        if user:
            user.locked_until = _as_aware_utc(user.locked_until)
        if user and user.locked_until and user.locked_until > now:
            if self._audit:
                self._audit.log(
                    AuditEventType.LOGIN_FAILURE,
                    email=email,
                    user_id=str(user.id),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Account locked.",
                )
            retry_after = max(int((user.locked_until - now).total_seconds()), 1)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        # Short-circuit for OAuth-only users who have no password_hash set.
        if (
            not user
            or not user.password_hash
            or not verify_password(password, user.password_hash)
        ):
            if user:
                await self._record_failed_login(user, ip_address, user_agent)
            if self._audit:
                self._audit.log(
                    AuditEventType.LOGIN_FAILURE,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Invalid credentials.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            if self._audit:
                self._audit.log(
                    AuditEventType.LOGIN_FAILURE,
                    email=email,
                    user_id=str(user.id),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Account disabled.",
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account disabled.",
            )

        roles, permissions = self._collect_claims(user)
        access_token, refresh_token, _, refresh_jti = self._build_token_pair(
            user, roles, permissions
        )

        user.failed_login_count = 0
        user.locked_until = None
        await self.user_repository.update_last_login(user)

        if self._audit:
            self._audit.log(
                AuditEventType.LOGIN_SUCCESS,
                email=email,
                user_id=str(user.id),
                jti=refresh_jti,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return TokenMatrixResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            user=UserOut.model_validate(user),
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    async def refresh(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenMatrixResponse:
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError) as exc:
            if self._audit:
                self._audit.log(
                    AuditEventType.TOKEN_REFRESH_FAILURE,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="JWT decode failure.",
                )
            raise _CREDENTIALS_EXCEPTION from exc

        token_type: str | None = payload.get("type")
        jti: str | None = payload.get("jti")
        sub: str | None = payload.get("sub")

        if token_type != "refresh" or not jti or not sub:  # noqa: S105
            if self._audit:
                self._audit.log(
                    AuditEventType.TOKEN_REFRESH_FAILURE,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Wrong token type or missing claims.",
                )
            raise _CREDENTIALS_EXCEPTION

        token_state = ACTIVE_REFRESH_TOKENS.get(jti)
        if token_state is None or token_state.get("revoked"):
            if self._audit:
                self._audit.log(
                    AuditEventType.TOKEN_REFRESH_FAILURE,
                    user_id=sub,
                    jti=jti,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="JTI not found or already revoked.",
                )
            raise _CREDENTIALS_EXCEPTION

        user = await self.user_repository.get_by_id(UUID(sub))
        if not user or not user.is_active:
            raise _CREDENTIALS_EXCEPTION

        # Revoke the consumed JTI before issuing the next pair (rotation).
        ACTIVE_REFRESH_TOKENS[jti]["revoked"] = True

        roles, permissions = self._collect_claims(user)
        access_token, new_refresh_token, _, new_refresh_jti = self._build_token_pair(
            user, roles, permissions
        )

        if self._audit:
            self._audit.log(
                AuditEventType.TOKEN_REFRESH,
                email=user.email,
                user_id=str(user.id),
                jti=new_refresh_jti,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return TokenMatrixResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",  # noqa: S106
            user=UserOut.model_validate(user),
        )

    async def _blacklist_access_token(self, access_token: str) -> None:
        """
        Best-effort: blacklist the caller's current access-token jti so it
        stops working immediately rather than riding out its remaining
        ~15-minute lifetime. Decoded defensively — an absent/garbled/
        already-expired access token must never block the refresh-token
        revocation that follows, which is logout's primary contract.
        """
        try:
            payload = jwt.decode(
                access_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError:
            return

        jti = payload.get("jti")
        exp = payload.get("exp")
        if not jti or not exp:
            return

        ttl_seconds = int(exp - datetime.now(UTC).timestamp())
        if ttl_seconds <= 0:
            return  # already expired — nothing to gain from blacklisting it
        await self._token_blacklist.add_jti(jti, ttl_seconds)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(
        self,
        refresh_token: str,
        *,
        access_token: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if access_token:
            await self._blacklist_access_token(access_token)

        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            ) from exc

        jti: str | None = payload.get("jti")
        sub: str | None = payload.get("sub")

        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        token_state = ACTIVE_REFRESH_TOKENS.get(jti)
        if token_state is None or token_state.get("revoked"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token already revoked.",
            )

        ACTIVE_REFRESH_TOKENS[jti]["revoked"] = True

        if self._audit:
            self._audit.log(
                AuditEventType.LOGOUT,
                user_id=sub,
                jti=jti,
                ip_address=ip_address,
                user_agent=user_agent,
            )
