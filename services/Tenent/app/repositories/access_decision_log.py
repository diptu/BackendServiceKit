"""Repository for AccessDecisionLog persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from app.models.access_decision_log import AccessDecisionLog
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class AccessDecisionLogRepository(BaseRepository[AccessDecisionLog]):
    async def create(self, log: AccessDecisionLog) -> AccessDecisionLog:
        self._session.add(log)
        await self._session.flush()
        await self._session.refresh(log)
        return log

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AccessDecisionLog]:
        base_where = [AccessDecisionLog.caller_tenant_id == tenant_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(AccessDecisionLog)
            .where(*base_where)
            .order_by(AccessDecisionLog.decided_at.desc(), AccessDecisionLog.id.desc())
        )

        if next_cursor:
            cursor_dt, cursor_id = decode_cursor(next_cursor)
            q = q.where(
                or_(
                    AccessDecisionLog.decided_at < cursor_dt,
                    (AccessDecisionLog.decided_at == cursor_dt)
                    & (AccessDecisionLog.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        cursor = (
            encode_cursor(items[-1].decided_at, items[-1].id)
            if has_more and items
            else None
        )
        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=cursor
        )
