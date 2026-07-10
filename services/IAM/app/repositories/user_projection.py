"""UserProjectionRepository — read-only access to the User Service projection.

No create/update/delete methods: UserProjection is written only by the
(deferred) user.created/updated/deleted event consumer, never by this
service's own API. See UserProjection's model docstring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.models.user_projection import UserProjection
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class UserProjectionFilter:
    tenant_id: UUID
    search: str | None = field(default=None)


class UserProjectionRepository(BaseRepository[UserProjection]):
    async def get_by_id(
        self, user_id: UUID, *, tenant_id: UUID
    ) -> UserProjection | None:
        stmt = select(UserProjection).where(
            UserProjection.id == user_id, UserProjection.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, filters: UserProjectionFilter) -> int:
        filtered: Select[tuple[UserProjection]] = select(UserProjection).where(
            UserProjection.tenant_id == filters.tenant_id
        )
        filtered = self._apply_search(filtered, filters)
        stmt = select(func.count()).select_from(filtered.subquery())
        result = await self._session.scalar(stmt)
        return result or 0

    async def list(
        self,
        *,
        filters: UserProjectionFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[UserProjection]:
        total = await self.count(filters)

        stmt: Select[tuple[UserProjection]] = select(UserProjection).where(
            UserProjection.tenant_id == filters.tenant_id
        )
        stmt = self._apply_search(stmt, filters)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    UserProjection.synced_at < cursor_dt,
                    and_(
                        UserProjection.synced_at == cursor_dt,
                        UserProjection.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            UserProjection.synced_at.desc(), UserProjection.id.desc()
        ).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[UserProjection] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.synced_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )

    @staticmethod
    def _apply_search(
        stmt: Select[tuple[UserProjection]], filters: UserProjectionFilter
    ) -> Select[tuple[UserProjection]]:
        if filters.search is not None:
            term = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    UserProjection.email.ilike(term),
                    UserProjection.display_name.ilike(term),
                )
            )
        return stmt
