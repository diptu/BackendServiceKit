"""Repository for RefreshToken."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    async def create(self, token: RefreshToken) -> RefreshToken:
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def get_by_hash(
        self, token_hash: str, *, tenant_id: UUID
    ) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_active_for_user(
        self, user_id: UUID, *, tenant_id: UUID
    ) -> list[RefreshToken]:
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.tenant_id == tenant_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return list(result.scalars())

    async def revoke(
        self, token_id: UUID, *, tenant_id: UUID, replaced_by: UUID | None = None
    ) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.tenant_id == tenant_id)
            .values(revoked_at=datetime.now(timezone.utc), replaced_by=replaced_by)
        )
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID, *, tenant_id: UUID) -> int:
        tokens = await self.list_active_for_user(user_id, tenant_id=tenant_id)
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)
        await self._session.flush()
        return len(tokens)
