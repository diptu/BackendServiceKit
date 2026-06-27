"""Repository for TenantLifecycleEvent — append-only audit log."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.tenant_lifecycle_event import TenantLifecycleEvent
from app.repositories.base import BaseRepository, PageResult


class LifecycleEventRepository(BaseRepository[TenantLifecycleEvent]):
    """Write-once operations for the tenant_lifecycle_events table."""

    async def append(self, event: TenantLifecycleEvent) -> TenantLifecycleEvent:
        """Insert a new lifecycle event record."""
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def list_by_tenant_id(
        self,
        tenant_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> PageResult[TenantLifecycleEvent]:
        """Return lifecycle events for a tenant ordered by occurred_at descending."""
        total_result = await self._session.scalar(
            select(func.count(TenantLifecycleEvent.id)).where(
                TenantLifecycleEvent.tenant_id == tenant_id
            )
        )
        total = total_result or 0

        result = await self._session.execute(
            select(TenantLifecycleEvent)
            .where(TenantLifecycleEvent.tenant_id == tenant_id)
            .order_by(TenantLifecycleEvent.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(result.scalars())

        return PageResult(
            items=items,
            total=total,
            has_more=(offset + len(items)) < total,
        )
