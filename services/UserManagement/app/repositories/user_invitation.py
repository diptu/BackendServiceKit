"""UserInvitationRepository — invitation CRUD, token-hash lookup."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select

from app.models.user_invitation import UserInvitation
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class UserInvitationRepository(BaseRepository[UserInvitation]):
    async def create(self, invitation: UserInvitation) -> UserInvitation:
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def save(self, invitation: UserInvitation) -> UserInvitation:
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def get_by_id(
        self, invitation_id: UUID, *, tenant_id: UUID | None = None
    ) -> UserInvitation | None:
        stmt = select(UserInvitation).where(UserInvitation.id == invitation_id)
        if tenant_id is not None:
            stmt = stmt.where(UserInvitation.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token_hash(self, token_hash: str) -> UserInvitation | None:
        result = await self._session.execute(
            select(UserInvitation).where(UserInvitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def count(self, tenant_id: UUID) -> int:
        result = await self._session.scalar(
            select(func.count(UserInvitation.id)).where(
                UserInvitation.tenant_id == tenant_id
            )
        )
        return result or 0

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[UserInvitation]:
        total = await self.count(tenant_id)

        stmt = select(UserInvitation).where(UserInvitation.tenant_id == tenant_id)

        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    UserInvitation.created_at < cursor_dt,
                    and_(
                        UserInvitation.created_at == cursor_dt,
                        UserInvitation.id < cursor_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            UserInvitation.created_at.desc(), UserInvitation.id.desc()
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
