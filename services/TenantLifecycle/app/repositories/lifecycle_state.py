"""Repository for TenantLifecycleState — current state per tenant."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.tenant_lifecycle_state import TenantLifecycleState
from app.repositories.base import BaseRepository


class LifecycleStateRepository(BaseRepository[TenantLifecycleState]):
    """CRUD operations for the tenant_lifecycle_states table."""

    async def create(self, state: TenantLifecycleState) -> TenantLifecycleState:
        """Persist a new lifecycle state record."""
        self._session.add(state)
        await self._session.flush()
        await self._session.refresh(state)
        return state

    async def save(self, state: TenantLifecycleState) -> TenantLifecycleState:
        """Flush in-memory changes to the database."""
        self._session.add(state)
        await self._session.flush()
        await self._session.refresh(state)
        return state

    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantLifecycleState | None:
        """Return the lifecycle state for a tenant, or None if not found."""
        result = await self._session.execute(
            select(TenantLifecycleState).where(
                TenantLifecycleState.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def exists_by_tenant_id(self, tenant_id: UUID) -> bool:
        """Return True if a lifecycle record exists for this tenant."""
        result = await self._session.scalar(
            select(func.count(TenantLifecycleState.id)).where(
                TenantLifecycleState.tenant_id == tenant_id
            )
        )
        return (result or 0) > 0
