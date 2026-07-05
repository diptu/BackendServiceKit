"""OrganizationMembershipRepository — organization<->user membership CRUD."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.models.organization_membership import OrganizationMembership
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class OrganizationMembershipRepository(BaseRepository[OrganizationMembership]):
    async def create(
        self, membership: OrganizationMembership
    ) -> OrganizationMembership:
        self._session.add(membership)
        await self._session.flush()
        await self._session.refresh(membership)
        return membership

    async def save(self, membership: OrganizationMembership) -> OrganizationMembership:
        self._session.add(membership)
        await self._session.flush()
        await self._session.refresh(membership)
        return membership

    async def delete(self, membership: OrganizationMembership) -> None:
        await self._session.delete(membership)
        await self._session.flush()

    async def get_by_user(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        result = await self._session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def count(self, organization_id: UUID) -> int:
        result = await self._session.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization_id
            )
        )
        return result or 0

    async def list_for_organization(
        self,
        organization_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationMembership]:
        total = await self.count(organization_id)

        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id
        )

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    OrganizationMembership.created_at < cursor_dt,
                    and_(
                        OrganizationMembership.created_at == cursor_dt,
                        OrganizationMembership.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            OrganizationMembership.created_at.desc(), OrganizationMembership.id.desc()
        ).limit(limit + 1)

        rows = list((await self._session.execute(stmt)).scalars())
        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor
        )
