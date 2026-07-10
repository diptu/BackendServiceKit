"""AuthService — credential lifecycle, login, token rotation, audit trail.

Every failure path returns/raises the same InvalidCredentialsError whether
the email is unknown or the password is wrong (see domain/exceptions.py) —
the Authentication skill this service was built against is explicit that
failure details must never leak which part was wrong.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import (
    ChangePasswordCmd,
    LoginCmd,
    ResetPasswordCmd,
    SetCredentialCmd,
)
from app.domain.enums import AuthEventType
from app.domain.exceptions import (
    AccountLockedError,
    CredentialAlreadyExistsError,
    CredentialNotFoundError,
    InvalidCredentialsError,
    PasswordResetTokenInvalidError,
    RefreshTokenInvalidError,
)
from app.models.auth_event import AuthEvent
from app.models.credential import Credential
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.repositories.auth_event import AuthEventRepository
from app.repositories.base import PageResult
from app.repositories.credential import CredentialRepository
from app.repositories.password_reset_token import PasswordResetTokenRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.services.mfa_service import MfaService
from app.services.password_hasher import hash_password, verify_password
from app.services.session_issuer import AuthTokenPair, issue_token_pair
from app.services.token_service import generate_opaque_token, hash_opaque_token

_PASSWORD_RESET_TTL = timedelta(hours=1)

# Re-exported so app.api / callers can keep importing AuthTokenPair from here;
# the canonical definition now lives in session_issuer (shared with OAuth/SSO).
__all__ = ["AuthService", "AuthTokenPair", "LoginResult"]


class LoginResult:
    """The outcome of a password login. Either a full token pair (`pair`) or,
    when the account has MFA enabled, a step-up handle (`mfa_token`) that must
    be redeemed at /auth/mfa/verify with a second factor. Exactly one is set."""

    __slots__ = ("pair", "mfa_token")

    def __init__(
        self, *, pair: AuthTokenPair | None = None, mfa_token: str | None = None
    ) -> None:
        self.pair = pair
        self.mfa_token = mfa_token

    @property
    def mfa_required(self) -> bool:
        return self.mfa_token is not None


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._credential_repo = CredentialRepository(session)
        self._refresh_repo = RefreshTokenRepository(session)
        self._reset_repo = PasswordResetTokenRepository(session)
        self._event_repo = AuthEventRepository(session)

    # ------------------------------------------------------------------
    # Credential lifecycle
    # ------------------------------------------------------------------

    async def set_credential(
        self, tenant_id: uuid.UUID, cmd: SetCredentialCmd
    ) -> Credential:
        if await self._credential_repo.exists_by_email(cmd.email, tenant_id=tenant_id):
            raise CredentialAlreadyExistsError(tenant_id, cmd.email)

        credential = Credential(
            user_id=cmd.user_id,
            tenant_id=tenant_id,
            email=cmd.email,
            password_hash=hash_password(cmd.password),
        )
        await self._credential_repo.create(credential)
        await self._log_event(
            tenant_id, cmd.user_id, AuthEventType.CREDENTIAL_SET, None
        )
        return credential

    # ------------------------------------------------------------------
    # Login / logout
    # ------------------------------------------------------------------

    async def login(self, tenant_id: uuid.UUID, cmd: LoginCmd) -> LoginResult:
        credential = await self._credential_repo.get_by_email(
            cmd.email, tenant_id=tenant_id
        )
        if credential is None:
            await self._log_event(tenant_id, None, AuthEventType.LOGIN_FAILURE, None)
            raise InvalidCredentialsError()

        now = datetime.now(timezone.utc)
        if (
            credential.locked_until is not None
            and _as_aware_utc(credential.locked_until) > now
        ):
            raise AccountLockedError(credential.locked_until.isoformat())

        if not verify_password(cmd.password, credential.password_hash):
            await self._register_failed_attempt(credential)
            await self._log_event(
                tenant_id, credential.user_id, AuthEventType.LOGIN_FAILURE, None
            )
            raise InvalidCredentialsError()

        credential.failed_login_attempts = 0
        credential.locked_until = None
        await self._credential_repo.save(credential)

        # Primary factor passed. If the account has a second factor enrolled,
        # don't hand out tokens yet — issue a step-up challenge instead and
        # only log a completed login once /auth/mfa/verify succeeds.
        mfa = MfaService(self._session)
        if await mfa.is_enabled(tenant_id, credential.user_id):
            mfa_token = await mfa.create_login_challenge(
                tenant_id, credential.user_id, device_info=cmd.device_info
            )
            return LoginResult(mfa_token=mfa_token)

        credential.last_login_at = now
        await self._credential_repo.save(credential)
        pair = await self._issue_token_pair(
            tenant_id, credential.user_id, device_info=cmd.device_info
        )
        await self._log_event(
            tenant_id, credential.user_id, AuthEventType.LOGIN_SUCCESS, None
        )
        return LoginResult(pair=pair)

    async def refresh(
        self, tenant_id: uuid.UUID, refresh_token_raw: str
    ) -> AuthTokenPair:
        token_hash = hash_opaque_token(refresh_token_raw)
        token = await self._refresh_repo.get_by_hash(token_hash, tenant_id=tenant_id)
        if token is None:
            raise RefreshTokenInvalidError()

        now = datetime.now(timezone.utc)
        if token.revoked_at is not None:
            # Reuse of an already-rotated (or already-logged-out) refresh
            # token — the standard refresh-token-replay signal. Treat as
            # compromised: revoke every other active token for this user too.
            await self._refresh_repo.revoke_all_for_user(
                token.user_id, tenant_id=tenant_id
            )
            raise RefreshTokenInvalidError()
        if _as_aware_utc(token.expires_at) <= now:
            raise RefreshTokenInvalidError()

        pair = await self._issue_token_pair(
            tenant_id, token.user_id, device_info=token.device_info
        )
        new_token_hash = hash_opaque_token(pair.refresh_token)
        new_token = await self._refresh_repo.get_by_hash(
            new_token_hash, tenant_id=tenant_id
        )
        assert new_token is not None
        await self._refresh_repo.revoke(
            token.id, tenant_id=tenant_id, replaced_by=new_token.id
        )
        await self._log_event(
            tenant_id, token.user_id, AuthEventType.TOKEN_REFRESHED, None
        )
        return pair

    async def logout(self, tenant_id: uuid.UUID, refresh_token_raw: str) -> None:
        token_hash = hash_opaque_token(refresh_token_raw)
        token = await self._refresh_repo.get_by_hash(token_hash, tenant_id=tenant_id)
        if token is None or token.revoked_at is not None:
            return  # idempotent — already logged out is not an error
        await self._refresh_repo.revoke(token.id, tenant_id=tenant_id)
        await self._log_event(tenant_id, token.user_id, AuthEventType.LOGOUT, None)

    async def logout_all(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> int:
        count = await self._refresh_repo.revoke_all_for_user(
            user_id, tenant_id=tenant_id
        )
        await self._log_event(tenant_id, user_id, AuthEventType.LOGOUT_ALL, None)
        return count

    # ------------------------------------------------------------------
    # Password change / reset
    # ------------------------------------------------------------------

    async def change_password(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, cmd: ChangePasswordCmd
    ) -> None:
        credential = await self._credential_repo.get_by_user_id(
            user_id, tenant_id=tenant_id
        )
        if credential is None:
            raise CredentialNotFoundError(user_id)
        if not verify_password(cmd.old_password, credential.password_hash):
            raise InvalidCredentialsError()

        credential.password_hash = hash_password(cmd.new_password)
        await self._credential_repo.save(credential)
        await self._refresh_repo.revoke_all_for_user(user_id, tenant_id=tenant_id)
        await self._log_event(tenant_id, user_id, AuthEventType.PASSWORD_CHANGED, None)

    async def request_password_reset(
        self, tenant_id: uuid.UUID, email: str
    ) -> str | None:
        """Always call this the same way regardless of the return value —
        callers must return an identical response whether or not `email` is
        registered, to avoid leaking which emails exist (user enumeration).
        Returns the raw reset token only for this build's own use (no
        NotificationService exists yet to deliver it out-of-band — see
        TODO.md); a production deployment must never return this value
        directly to the caller."""
        credential = await self._credential_repo.get_by_email(
            email, tenant_id=tenant_id
        )
        if credential is None:
            return None

        raw_token, token_hash = generate_opaque_token()
        now = datetime.now(timezone.utc)
        await self._reset_repo.create(
            PasswordResetToken(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=credential.user_id,
                token_hash=token_hash,
                created_at=now,
                expires_at=now + _PASSWORD_RESET_TTL,
            )
        )
        await self._log_event(
            tenant_id,
            credential.user_id,
            AuthEventType.PASSWORD_RESET_REQUESTED,
            None,
        )
        return raw_token

    async def reset_password(self, tenant_id: uuid.UUID, cmd: ResetPasswordCmd) -> None:
        token_hash = hash_opaque_token(cmd.token)
        reset_token = await self._reset_repo.get_by_hash(
            token_hash, tenant_id=tenant_id
        )
        now = datetime.now(timezone.utc)
        if (
            reset_token is None
            or reset_token.used_at is not None
            or _as_aware_utc(reset_token.expires_at) <= now
        ):
            raise PasswordResetTokenInvalidError()

        credential = await self._credential_repo.get_by_user_id(
            reset_token.user_id, tenant_id=tenant_id
        )
        if credential is None:
            raise PasswordResetTokenInvalidError()

        credential.password_hash = hash_password(cmd.new_password)
        await self._credential_repo.save(credential)
        await self._reset_repo.mark_used(reset_token)
        await self._refresh_repo.revoke_all_for_user(
            credential.user_id, tenant_id=tenant_id
        )
        await self._log_event(
            tenant_id,
            credential.user_id,
            AuthEventType.PASSWORD_RESET_COMPLETED,
            None,
        )

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def list_sessions(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[RefreshToken]:
        return await self._refresh_repo.list_active_for_user(
            user_id, tenant_id=tenant_id
        )

    async def revoke_session(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> None:
        sessions = await self.list_sessions(tenant_id, user_id)
        if not any(s.id == session_id for s in sessions):
            return  # not found or not owned by this user — no-op, not a leak
        await self._refresh_repo.revoke(session_id, tenant_id=tenant_id)

    async def list_events(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AuthEvent]:
        return await self._event_repo.list_by_user(
            user_id, tenant_id=tenant_id, cursor=cursor, limit=limit
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _register_failed_attempt(self, credential: Credential) -> None:
        from app.core.config import settings

        credential.failed_login_attempts += 1
        if credential.failed_login_attempts >= settings.max_failed_login_attempts:
            credential.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.account_lockout_minutes
            )
        await self._credential_repo.save(credential)

    async def _issue_token_pair(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        device_info: str | None = None,
    ) -> AuthTokenPair:
        return await issue_token_pair(
            self._session, tenant_id, user_id, device_info=device_info
        )

    async def _log_event(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        event_type: AuthEventType,
        detail: str | None,
    ) -> None:
        await self._event_repo.create(
            AuthEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                detail=detail,
            )
        )


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on DateTime(timezone=True) columns (Postgres
    doesn't) — treat a naive value read back from the DB as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
