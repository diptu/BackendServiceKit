"""Repository for PasswordResetToken."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.models.password_reset_token import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def get_by_hash(
        self, token_hash: str, *, tenant_id: UUID
    ) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordResetToken) -> None:
        token.used_at = datetime.now(timezone.utc)
        await self._session.flush()
