"""Repository for UserStatusHistory (append-only audit log).

Orders and paginates by `seq` (a monotonic auto-increment column), not
`occurred_at` + the UUID primary key — `occurred_at` alone can collide
(SQLite's `now()` is second-resolution) and the UUID isn't time-ordered,
so that combination doesn't reliably preserve "most recent transition
first." `seq` always does. The cursor is just the seq value itself, not
the generic base64 (timestamp, UUID) cursor used elsewhere in this
service — simpler, and correct for the same reason.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.user_status_history import UserStatusHistory
from app.repositories.base import BaseRepository, PageResult


class UserStatusHistoryRepository(BaseRepository[UserStatusHistory]):
    async def create(self, entry: UserStatusHistory) -> UserStatusHistory:
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[UserStatusHistory]:
        base_where = [UserStatusHistory.user_id == user_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(UserStatusHistory)
            .where(*base_where)
            .order_by(UserStatusHistory.seq.desc())
        )

        if cursor:
            q = q.where(UserStatusHistory.seq < int(cursor))

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        next_cursor = str(items[-1].seq) if has_more and items else None
        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor
        )
