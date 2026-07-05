"""Repository for UserProfile."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.user_profile import UserProfile
from app.repositories.base import BaseRepository


class UserProfileRepository(BaseRepository[UserProfile]):
    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def save(self, profile: UserProfile) -> UserProfile:
        self._session.add(profile)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile
