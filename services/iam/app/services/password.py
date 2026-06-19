import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status

from app.audit.events import AuditEventType
from app.audit.logger import AuditLogger
from app.core.config import settings
from app.core.security import (
    hash_password,
    password_matches_identifier,
    verify_password,
)
from app.core.token_blacklist import TokenBlacklist, get_token_blacklist
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.repositories.password_reset import PasswordResetTokenRepository
from app.repositories.user import UserRepository
from app.services.email import EmailService


class PasswordService:
    def __init__(
        self,
        user_repository: UserRepository,
        reset_token_repository: PasswordResetTokenRepository,
        email_service: EmailService,
        audit_logger: AuditLogger | None = None,
        token_blacklist: TokenBlacklist | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.reset_token_repository = reset_token_repository
        self.email_service = email_service
        self._audit = audit_logger
        self._token_blacklist = token_blacklist or get_token_blacklist()

    async def _invalidate_prior_access_tokens(self, user: User) -> None:
        """Mark every access token issued before now as invalid (see
        app.core.token_blacklist for why this is a timestamp comparison
        rather than an enumerated jti blacklist). Uses full float
        precision (matching the access token's `iat` claim, see
        AuthService._build_token_pair) rather than whole seconds — integer
        seconds collide too easily between "token just issued" and
        "password just changed" in rapid succession."""
        changed_at = datetime.now(UTC)
        user.password_changed_at = changed_at
        await self._token_blacklist.set_invalidate_before(
            str(user.id),
            timestamp=changed_at.timestamp(),
            ttl_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ------------------------------------------------------------------
    # Change password (authenticated)
    # ------------------------------------------------------------------

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        user = await self.user_repository.get_by_id(user_id)

        if not user or not verify_password(current_password, user.password_hash):  # type: ignore[arg-type]
            if self._audit:
                self._audit.log(
                    AuditEventType.PASSWORD_CHANGE_FAILURE,
                    user_id=str(user_id),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Incorrect current password.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

        if password_matches_identifier(new_password, user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not match your email address.",
            )

        user.password_hash = hash_password(new_password)
        await self._invalidate_prior_access_tokens(user)
        await self.user_repository.save(user)

        if self._audit:
            self._audit.log(
                AuditEventType.PASSWORD_CHANGED,
                email=user.email,
                user_id=str(user.id),
                ip_address=ip_address,
                user_agent=user_agent,
            )

    # ------------------------------------------------------------------
    # Forgot password (unauthenticated — always succeeds to prevent enumeration)
    # ------------------------------------------------------------------

    async def forgot_password(
        self,
        email: str,
        *,
        ip_address: str | None = None,
    ) -> None:
        user = await self.user_repository.get_by_email(email.strip().lower())

        # Silently return for unknown / inactive accounts — no information leaked
        if not user or not user.is_active:
            return

        token_model, raw_token = PasswordResetToken.generate(
            user.id, ttl_minutes=settings.RESET_TOKEN_TTL_MINUTES
        )
        await self.reset_token_repository.create(token_model)
        await self.email_service.send_password_reset(email, raw_token)

        if self._audit:
            self._audit.log(
                AuditEventType.PASSWORD_RESET_REQUESTED,
                email=email,
                user_id=str(user.id),
                ip_address=ip_address,
            )

    # ------------------------------------------------------------------
    # Reset password (unauthenticated — consumes a single-use token)
    # ------------------------------------------------------------------

    async def reset_password(
        self,
        raw_token: str,
        new_password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token_model = await self.reset_token_repository.get_by_hash(token_hash)

        if not token_model or not token_model.is_valid:
            if self._audit:
                self._audit.log(
                    AuditEventType.PASSWORD_RESET_FAILURE,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Invalid or expired reset token.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token.",
            )

        # Mark consumed BEFORE writing the new hash — prevents a double-use
        # race condition where two concurrent requests both pass is_valid.
        await self.reset_token_repository.mark_used(token_model)

        user = await self.user_repository.get_by_id(token_model.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token.",
            )

        if password_matches_identifier(new_password, user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must not match your email address.",
            )

        user.password_hash = hash_password(new_password)
        await self._invalidate_prior_access_tokens(user)
        await self.user_repository.save(user)

        if self._audit:
            self._audit.log(
                AuditEventType.PASSWORD_RESET_SUCCESS,
                email=user.email,
                user_id=str(user.id),
                ip_address=ip_address,
                user_agent=user_agent,
            )
