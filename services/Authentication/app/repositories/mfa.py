"""Repositories for the MFA aggregate (secret, recovery codes, challenges).

Every lookup takes tenant_id as a required keyword argument — never optional —
the same guard the rest of this service's repositories use against an
accidental cross-tenant read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select, update

from app.models.mfa_challenge import MfaChallenge
from app.models.mfa_recovery_code import MfaRecoveryCode
from app.models.mfa_secret import MfaSecret
from app.repositories.base import BaseRepository


class MfaSecretRepository(BaseRepository[MfaSecret]):
    async def get(self, user_id: UUID, *, tenant_id: UUID) -> MfaSecret | None:
        result = await self._session.execute(
            select(MfaSecret).where(
                MfaSecret.user_id == user_id, MfaSecret.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, secret: MfaSecret) -> MfaSecret:
        await self._session.merge(secret)
        await self._session.flush()
        return secret

    async def save(self, secret: MfaSecret) -> MfaSecret:
        self._session.add(secret)
        await self._session.flush()
        return secret

    async def delete(self, user_id: UUID, *, tenant_id: UUID) -> None:
        await self._session.execute(
            delete(MfaSecret).where(
                MfaSecret.user_id == user_id, MfaSecret.tenant_id == tenant_id
            )
        )
        await self._session.flush()


class MfaRecoveryCodeRepository(BaseRepository[MfaRecoveryCode]):
    async def add_all(self, codes: list[MfaRecoveryCode]) -> None:
        self._session.add_all(codes)
        await self._session.flush()

    async def get_unused_by_hash(
        self, code_hash: str, user_id: UUID, *, tenant_id: UUID
    ) -> MfaRecoveryCode | None:
        result = await self._session.execute(
            select(MfaRecoveryCode).where(
                MfaRecoveryCode.code_hash == code_hash,
                MfaRecoveryCode.user_id == user_id,
                MfaRecoveryCode.tenant_id == tenant_id,
                MfaRecoveryCode.used_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, code: MfaRecoveryCode) -> None:
        code.used_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def delete_for_user(self, user_id: UUID, *, tenant_id: UUID) -> None:
        await self._session.execute(
            delete(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == user_id,
                MfaRecoveryCode.tenant_id == tenant_id,
            )
        )
        await self._session.flush()


class MfaChallengeRepository(BaseRepository[MfaChallenge]):
    async def create(self, challenge: MfaChallenge) -> MfaChallenge:
        self._session.add(challenge)
        await self._session.flush()
        return challenge

    async def get_by_hash(
        self, token_hash: str, *, tenant_id: UUID
    ) -> MfaChallenge | None:
        result = await self._session.execute(
            select(MfaChallenge).where(
                MfaChallenge.token_hash == token_hash,
                MfaChallenge.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, challenge_id: UUID, *, tenant_id: UUID) -> None:
        await self._session.execute(
            update(MfaChallenge)
            .where(
                MfaChallenge.id == challenge_id,
                MfaChallenge.tenant_id == tenant_id,
            )
            .values(consumed_at=datetime.now(timezone.utc))
        )
        await self._session.flush()
