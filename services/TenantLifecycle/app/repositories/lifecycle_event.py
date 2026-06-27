"""Repository for TenantLifecycleEvent — append-only audit log."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.models.tenant_lifecycle_event import TenantLifecycleEvent
from app.repositories.base import BaseRepository, PageResult, decode_cursor, encode_cursor


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
        next_cursor: str | None = None,
    ) -> PageResult[TenantLifecycleEvent]:
        """Return lifecycle events for a tenant ordered by occurred_at descending.

        Uses keyset pagination: pass next_cursor from the previous response to
        advance to the next page. Omit (or pass None) for the first page.
        """
        total_result = await self._session.scalar(
            select(func.count(TenantLifecycleEvent.id)).where(
                TenantLifecycleEvent.tenant_id == tenant_id
            )
        )
        total = total_result or 0

        stmt = (
            select(TenantLifecycleEvent)
            .where(TenantLifecycleEvent.tenant_id == tenant_id)
            .order_by(
                TenantLifecycleEvent.occurred_at.desc(),
                TenantLifecycleEvent.id.desc(),
            )
            .limit(limit)
        )

        if next_cursor is not None:
            cursor_dt, cursor_id = decode_cursor(next_cursor)
            stmt = stmt.where(
                or_(
                    TenantLifecycleEvent.occurred_at < cursor_dt,
                    and_(
                        TenantLifecycleEvent.occurred_at == cursor_dt,
                        TenantLifecycleEvent.id < cursor_id,
                    ),
                )
            )

        result = await self._session.execute(stmt)
        items = list(result.scalars())

        encoded_next: str | None = None
        if len(items) == limit:
            last = items[-1]
            encoded_next = encode_cursor(last.occurred_at, last.id)

        return PageResult(
            items=items,
            total=total,
            has_more=encoded_next is not None,
            next_cursor=encoded_next,
        )
