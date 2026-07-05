"""AccessReviewRepository — access-governance review CRUD."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from app.models.access_review import AccessReview
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


@dataclass
class AccessReviewFilter:
    tenant_id: UUID


class AccessReviewRepository(BaseRepository[AccessReview]):
    async def create(self, access_review: AccessReview) -> AccessReview:
        self._session.add(access_review)
        await self._session.flush()
        await self._session.refresh(access_review)
        return access_review

    async def save(self, access_review: AccessReview) -> AccessReview:
        self._session.add(access_review)
        await self._session.flush()
        await self._session.refresh(access_review)
        return access_review

    async def get_by_id(
        self, access_review_id: UUID, *, tenant_id: UUID | None = None
    ) -> AccessReview | None:
        stmt = select(AccessReview).where(AccessReview.id == access_review_id)
        if tenant_id is not None:
            stmt = stmt.where(AccessReview.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self, filters: AccessReviewFilter) -> int:
        result = await self._session.scalar(
            select(func.count(AccessReview.id)).where(
                AccessReview.tenant_id == filters.tenant_id
            )
        )
        return result or 0

    async def list(
        self,
        *,
        filters: AccessReviewFilter,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AccessReview]:
        total = await self.count(filters)

        stmt: Select[tuple[AccessReview]] = select(AccessReview).where(
            AccessReview.tenant_id == filters.tenant_id
        )

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    AccessReview.created_at < cursor_dt,
                    and_(
                        AccessReview.created_at == cursor_dt,
                        AccessReview.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            AccessReview.created_at.desc(), AccessReview.id.desc()
        ).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[AccessReview] = list(result.scalars())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, next_cursor=next_cursor, has_more=has_more
        )
