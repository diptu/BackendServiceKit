"""Repository for AuthEvent — append-only, ordered by seq (see model docstring).

Cursor here is just `str(seq)` — a plain integer offset, not the
datetime+UUID keyset cursor `repositories.base.encode_cursor` builds for
every other paginated list in this repo. AuthEvent's own primary key
already is the ordering key, so wrapping it in that helper would be
indirection for no benefit.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.models.auth_event import AuthEvent
from app.repositories.base import BaseRepository, PageResult


class AuthEventRepository(BaseRepository[AuthEvent]):
    async def create(self, event: AuthEvent) -> AuthEvent:
        self._session.add(event)
        await self._session.flush()
        await self._session.refresh(event)
        return event

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        tenant_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AuthEvent]:
        base_where = [
            AuthEvent.user_id == user_id,
            AuthEvent.tenant_id == tenant_id,
        ]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = select(AuthEvent).where(*base_where).order_by(AuthEvent.seq.desc())

        if cursor:
            try:
                cursor_seq = int(cursor)
            except ValueError as exc:
                raise ValueError(f"Invalid pagination cursor: {cursor!r}") from exc
            q = q.where(AuthEvent.seq < cursor_seq)

        q = q.limit(limit + 1)
        rows = list((await self._session.execute(q)).scalars().all())

        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = str(items[-1].seq) if has_more and items else None

        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor
        )
