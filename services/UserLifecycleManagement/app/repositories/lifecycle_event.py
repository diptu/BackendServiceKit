"""Repository for LifecycleEvent (append-only audit log).

Mirrors UserManagement's own UserStatusHistoryRepository shape.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.lifecycle_event import LifecycleEvent
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class LifecycleEventRepository(BaseRepository[LifecycleEvent]):
    async def create(self, event: LifecycleEvent) -> LifecycleEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def get_latest_by_user(self, user_id: UUID) -> LifecycleEvent | None:
        result = await self._session.execute(
            select(LifecycleEvent)
            .where(LifecycleEvent.user_id == user_id)
            .order_by(LifecycleEvent.occurred_at.desc(), LifecycleEvent.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[LifecycleEvent]:
        base_where = [LifecycleEvent.user_id == user_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(LifecycleEvent)
            .where(*base_where)
            .order_by(LifecycleEvent.occurred_at.desc(), LifecycleEvent.id.desc())
        )

        if cursor:
            cursor_dt, cursor_id = decode_cursor(cursor)
            q = q.where(
                or_(
                    LifecycleEvent.occurred_at < cursor_dt,
                    (LifecycleEvent.occurred_at == cursor_dt)
                    & (LifecycleEvent.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        next_cursor = (
            encode_cursor(items[-1].occurred_at, items[-1].id)
            if has_more and items
            else None
        )
        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor
        )
