"""OrganizationInvitationRepository — invitation CRUD, token-hash lookup."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.models.organization_invitation import OrganizationInvitation
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class OrganizationInvitationRepository(BaseRepository[OrganizationInvitation]):
    async def create(
        self, invitation: OrganizationInvitation
    ) -> OrganizationInvitation:
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def save(self, invitation: OrganizationInvitation) -> OrganizationInvitation:
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def get_by_id(
        self, invitation_id: UUID, *, organization_id: UUID | None = None
    ) -> OrganizationInvitation | None:
        stmt = select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id
        )
        if organization_id is not None:
            stmt = stmt.where(OrganizationInvitation.organization_id == organization_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        result = await self._session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def count(self, organization_id: UUID) -> int:
        result = await self._session.scalar(
            select(func.count(OrganizationInvitation.id)).where(
                OrganizationInvitation.organization_id == organization_id
            )
        )
        return result or 0

    async def list_for_organization(
        self,
        organization_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[OrganizationInvitation]:
        total = await self.count(organization_id)

        stmt = select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == organization_id
        )

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    OrganizationInvitation.created_at < cursor_dt,
                    and_(
                        OrganizationInvitation.created_at == cursor_dt,
                        OrganizationInvitation.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            OrganizationInvitation.created_at.desc(), OrganizationInvitation.id.desc()
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
