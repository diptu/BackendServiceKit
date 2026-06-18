from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.config import settings
from app.core.rbac import DEFAULT_ROLE
from app.core.security import create_access_token, hash_password, verify_password
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


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.role_repository = role_repository
        self._audit = audit_logger

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

        access_claims: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
            "jti": access_jti,
            "roles": roles,
            "permissions": permissions,
            "type": "access",
        }
        refresh_claims: dict[str, Any] = {
            "sub": str(user.id),
            "jti": refresh_jti,
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
        roles = [role.name for role in user.roles]
        permissions = list({p.name for role in user.roles for p in role.permissions})
        return roles, permissions

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------

    async def register(self, payload: UserCreate) -> User:
        email = payload.email.strip().lower()

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

        user = await self.user_repository.get_by_email(email)

        if not user or not verify_password(password, user.password_hash):
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

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(
        self,
        refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
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
