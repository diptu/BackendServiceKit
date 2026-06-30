"""Repository for IsolationPolicy persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select, update

from app.models.isolation_policy import IsolationPolicy
from app.repositories.base import BaseRepository, PageResult, decode_cursor, encode_cursor


class IsolationPolicyRepository(BaseRepository[IsolationPolicy]):

    async def create(self, policy: IsolationPolicy) -> IsolationPolicy:
        self._session.add(policy)
        await self._session.flush()
        await self._session.refresh(policy)
        return policy

    async def get_by_id(self, policy_id: UUID) -> IsolationPolicy | None:
        result = await self._session.execute(
            select(IsolationPolicy).where(IsolationPolicy.id == policy_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_tenant(self, tenant_id: UUID) -> IsolationPolicy | None:
        result = await self._session.execute(
            select(IsolationPolicy).where(
                IsolationPolicy.tenant_id == tenant_id,
                IsolationPolicy.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[IsolationPolicy]:
        base_where = [IsolationPolicy.tenant_id == tenant_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(IsolationPolicy)
            .where(*base_where)
            .order_by(IsolationPolicy.created_at.desc(), IsolationPolicy.id.desc())
        )

        if next_cursor:
            cursor_dt, cursor_id = decode_cursor(next_cursor)
            q = q.where(
                or_(
                    IsolationPolicy.created_at < cursor_dt,
                    (IsolationPolicy.created_at == cursor_dt)
                    & (IsolationPolicy.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None
        )
        return PageResult(items=items, total=total, has_more=has_more, next_cursor=cursor)

    async def update(self, policy_id: UUID, **kwargs: object) -> IsolationPolicy:
        await self._session.execute(
            update(IsolationPolicy)
            .where(IsolationPolicy.id == policy_id)
            .values(**kwargs)
        )
        await self._session.flush()
        policy = await self.get_by_id(policy_id)
        assert policy is not None
        return policy

    async def toggle_active(self, policy_id: UUID, *, is_active: bool) -> IsolationPolicy:
        return await self.update(policy_id, is_active=is_active)
