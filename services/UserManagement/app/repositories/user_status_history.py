"""Repository for UserStatusHistory (append-only audit log).

Mirrors services/Tenent/app/repositories/lifecycle_event.py's shape exactly.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.user_status_history import UserStatusHistory
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


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
            .order_by(UserStatusHistory.occurred_at.desc(), UserStatusHistory.id.desc())
        )

        if cursor:
            cursor_dt, cursor_id = decode_cursor(cursor)
            q = q.where(
                or_(
                    UserStatusHistory.occurred_at < cursor_dt,
                    (UserStatusHistory.occurred_at == cursor_dt)
                    & (UserStatusHistory.id < cursor_id),
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
