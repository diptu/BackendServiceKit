"""Repository for LifecycleState — one row per user this service has acted on."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.lifecycle_state import LifecycleState
from app.repositories.base import BaseRepository


class LifecycleStateRepository(BaseRepository[LifecycleState]):
    async def get_by_user_id(self, user_id: UUID) -> LifecycleState | None:
        result = await self._session.execute(
            select(LifecycleState).where(LifecycleState.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def save(self, state: LifecycleState) -> LifecycleState:
        self._session.add(state)
        await self._session.flush()
        await self._session.refresh(state)
        return state
