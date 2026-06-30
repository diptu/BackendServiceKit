"""Repository for TenantLifecycleState (current status per tenant)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.lifecycle_state import TenantLifecycleState
from app.repositories.base import BaseRepository


class LifecycleStateRepository(BaseRepository[TenantLifecycleState]):
    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantLifecycleState | None:
        result = await self._session.execute(
            select(TenantLifecycleState).where(
                TenantLifecycleState.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, state: TenantLifecycleState) -> TenantLifecycleState:
        self._session.add(state)
        await self._session.flush()
        await self._session.refresh(state)
        return state

    async def save(self, state: TenantLifecycleState) -> TenantLifecycleState:
        self._session.add(state)
        await self._session.flush()
        await self._session.refresh(state)
        return state
