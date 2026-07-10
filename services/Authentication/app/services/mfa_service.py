"""MfaService — TOTP enrollment, login step-up, and recovery codes.

Enrollment is two-phase: `setup` writes an *unconfirmed* secret and hands
back the provisioning URI + one-time recovery codes; MFA only becomes
enforced once `activate` sees a valid code proving the user really scanned
it. Once enforced, password login no longer returns tokens directly — it
returns a challenge handle (`create_login_challenge`) that must be redeemed
with a second factor via `verify_login`.

Every wrong-factor path raises the single `InvalidMfaCodeError`, the same
no-detail-leak discipline `InvalidCredentialsError` uses for passwords.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import AuthEventType
from app.domain.exceptions import (
    InvalidMfaCodeError,
    MfaAlreadyEnabledError,
    MfaNotEnrolledError,
)
from app.models.auth_event import AuthEvent
from app.models.mfa_challenge import MfaChallenge
from app.models.mfa_recovery_code import MfaRecoveryCode
from app.models.mfa_secret import MfaSecret
from app.repositories.auth_event import AuthEventRepository
from app.repositories.mfa import (
    MfaChallengeRepository,
    MfaRecoveryCodeRepository,
    MfaSecretRepository,
)
from app.services.session_issuer import AuthTokenPair, issue_token_pair
from app.services.token_service import generate_opaque_token, hash_opaque_token


class MfaEnrollment:
    """The one-time material returned by setup — never persisted in the
    clear and never retrievable again after this response."""

    __slots__ = ("secret", "otpauth_uri", "recovery_codes")

    def __init__(
        self, secret: str, otpauth_uri: str, recovery_codes: list[str]
    ) -> None:
        self.secret = secret
        self.otpauth_uri = otpauth_uri
        self.recovery_codes = recovery_codes


def _hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.replace("-", "").lower().encode()).hexdigest()


def _generate_recovery_code() -> str:
    raw = secrets.token_hex(5)  # 10 hex chars
    return f"{raw[:5]}-{raw[5:]}"


def _as_aware_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class MfaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._secrets = MfaSecretRepository(session)
        self._recovery = MfaRecoveryCodeRepository(session)
        self._challenges = MfaChallengeRepository(session)
        self._events = AuthEventRepository(session)

    async def is_enabled(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        secret = await self._secrets.get(user_id, tenant_id=tenant_id)
        return secret is not None and secret.confirmed

    async def setup(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, account_label: str
    ) -> MfaEnrollment:
        existing = await self._secrets.get(user_id, tenant_id=tenant_id)
        if existing is not None and existing.confirmed:
            raise MfaAlreadyEnabledError()

        secret_value = pyotp.random_base32()
        now = datetime.now(timezone.utc)
        await self._secrets.upsert(
            MfaSecret(
                tenant_id=tenant_id,
                user_id=user_id,
                secret=secret_value,
                confirmed=False,
                created_at=now,
                confirmed_at=None,
            )
        )

        # Fresh recovery codes supersede any from an earlier, abandoned setup.
        await self._recovery.delete_for_user(user_id, tenant_id=tenant_id)
        raw_codes = [
            _generate_recovery_code() for _ in range(settings.mfa_recovery_code_count)
        ]
        await self._recovery.add_all(
            [
                MfaRecoveryCode(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    code_hash=_hash_recovery_code(code),
                )
                for code in raw_codes
            ]
        )

        otpauth_uri = pyotp.TOTP(secret_value).provisioning_uri(
            name=account_label, issuer_name=settings.mfa_issuer_name
        )
        await self._log(tenant_id, user_id, AuthEventType.MFA_SETUP_STARTED)
        return MfaEnrollment(secret_value, otpauth_uri, raw_codes)

    async def activate(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, code: str
    ) -> None:
        secret = await self._secrets.get(user_id, tenant_id=tenant_id)
        if secret is None:
            raise MfaNotEnrolledError()
        if secret.confirmed:
            raise MfaAlreadyEnabledError()
        if not _verify_totp(secret.secret, code):
            await self._log(tenant_id, user_id, AuthEventType.MFA_FAILURE)
            raise InvalidMfaCodeError()

        secret.confirmed = True
        secret.confirmed_at = datetime.now(timezone.utc)
        await self._secrets.save(secret)
        await self._log(tenant_id, user_id, AuthEventType.MFA_ENABLED)

    async def disable(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, code: str
    ) -> None:
        secret = await self._secrets.get(user_id, tenant_id=tenant_id)
        if secret is None or not secret.confirmed:
            raise MfaNotEnrolledError()
        if not await self._verify_second_factor(tenant_id, user_id, secret, code):
            await self._log(tenant_id, user_id, AuthEventType.MFA_FAILURE)
            raise InvalidMfaCodeError()

        await self._secrets.delete(user_id, tenant_id=tenant_id)
        await self._recovery.delete_for_user(user_id, tenant_id=tenant_id)
        await self._log(tenant_id, user_id, AuthEventType.MFA_DISABLED)

    async def create_login_challenge(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        device_info: str | None = None,
    ) -> str:
        raw_token, token_hash = generate_opaque_token()
        now = datetime.now(timezone.utc)
        await self._challenges.create(
            MfaChallenge(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                token_hash=token_hash,
                device_info=device_info,
                created_at=now,
                expires_at=now + timedelta(seconds=settings.mfa_challenge_ttl_seconds),
            )
        )
        await self._log(tenant_id, user_id, AuthEventType.MFA_CHALLENGE_ISSUED)
        return raw_token

    async def verify_login(
        self, tenant_id: uuid.UUID, mfa_token: str, code: str
    ) -> AuthTokenPair:
        challenge = await self._challenges.get_by_hash(
            hash_opaque_token(mfa_token), tenant_id=tenant_id
        )
        now = datetime.now(timezone.utc)
        if (
            challenge is None
            or challenge.consumed_at is not None
            or _as_aware_utc(challenge.expires_at) <= now
        ):
            raise InvalidMfaCodeError()

        secret = await self._secrets.get(challenge.user_id, tenant_id=tenant_id)
        if secret is None or not secret.confirmed:
            raise InvalidMfaCodeError()

        if not await self._verify_second_factor(
            tenant_id, challenge.user_id, secret, code
        ):
            await self._log(tenant_id, challenge.user_id, AuthEventType.MFA_FAILURE)
            raise InvalidMfaCodeError()

        # Single-use: burn the challenge before minting the session.
        await self._challenges.consume(challenge.id, tenant_id=tenant_id)
        pair = await issue_token_pair(
            self._session,
            tenant_id,
            challenge.user_id,
            device_info=challenge.device_info,
        )
        await self._log(tenant_id, challenge.user_id, AuthEventType.MFA_VERIFIED)
        return pair

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _verify_second_factor(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        secret: MfaSecret,
        code: str,
    ) -> bool:
        if _verify_totp(secret.secret, code):
            return True
        recovery = await self._recovery.get_unused_by_hash(
            _hash_recovery_code(code), user_id, tenant_id=tenant_id
        )
        if recovery is not None:
            await self._recovery.mark_used(recovery)
            return True
        return False

    async def _log(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        event_type: AuthEventType,
    ) -> None:
        await self._events.create(
            AuthEvent(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                detail=None,
            )
        )


def _verify_totp(secret: str, code: str) -> bool:
    # valid_window=1 tolerates a single 30s step of clock skew each way.
    return bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=1))
