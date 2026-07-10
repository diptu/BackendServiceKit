"""Repository for Avatar."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.avatar import Avatar
from app.repositories.base import BaseRepository


class AvatarRepository(BaseRepository[Avatar]):
    async def get_by_user_id(self, user_id: UUID, *, tenant_id: UUID) -> Avatar | None:
        result = await self._session.execute(
            select(Avatar).where(
                Avatar.user_id == user_id, Avatar.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def save(self, avatar: Avatar) -> Avatar:
        self._session.add(avatar)
        await self._session.flush()
        await self._session.refresh(avatar)
        return avatar

    async def delete(self, avatar: Avatar) -> None:
        await self._session.delete(avatar)
        await self._session.flush()
