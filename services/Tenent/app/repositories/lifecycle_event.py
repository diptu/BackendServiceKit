"""Repository for TenantLifecycleEvent (append-only audit log)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.lifecycle_event import TenantLifecycleEvent
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class LifecycleEventRepository(BaseRepository[TenantLifecycleEvent]):
    async def create(self, event: TenantLifecycleEvent) -> TenantLifecycleEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[TenantLifecycleEvent]:
        base_where = [TenantLifecycleEvent.tenant_id == tenant_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(TenantLifecycleEvent)
            .where(*base_where)
            .order_by(
                TenantLifecycleEvent.occurred_at.desc(),
                TenantLifecycleEvent.id.desc(),
            )
        )

        if next_cursor:
            cursor_dt, cursor_id = decode_cursor(next_cursor)
            q = q.where(
                or_(
                    TenantLifecycleEvent.occurred_at < cursor_dt,
                    (TenantLifecycleEvent.occurred_at == cursor_dt)
                    & (TenantLifecycleEvent.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        cursor = (
            encode_cursor(items[-1].occurred_at, items[-1].id)
            if has_more and items
            else None
        )
        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=cursor
        )
