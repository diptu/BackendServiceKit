"""Repository for UserPreferences."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.user_preferences import UserPreferences
from app.repositories.base import BaseRepository


class UserPreferencesRepository(BaseRepository[UserPreferences]):
    async def get_by_user_id(
        self, user_id: UUID, *, tenant_id: UUID
    ) -> UserPreferences | None:
        result = await self._session.execute(
            select(UserPreferences).where(
                UserPreferences.user_id == user_id,
                UserPreferences.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def save(self, preferences: UserPreferences) -> UserPreferences:
        self._session.add(preferences)
        await self._session.flush()
        await self._session.refresh(preferences)
        return preferences
