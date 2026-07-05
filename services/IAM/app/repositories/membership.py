"""TenantMembershipRepository — user<->tenant membership."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select

from app.domain.enums import MembershipStatus
from app.models.membership import TenantMembership
from app.repositories.base import BaseRepository


class TenantMembershipRepository(BaseRepository[TenantMembership]):
    async def exists(self, tenant_id: UUID, user_id: UUID) -> bool:
        result = await self._session.scalar(
            select(func.count())
            .select_from(TenantMembership)
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        return (result or 0) > 0

    async def add(self, tenant_id: UUID, user_id: UUID) -> TenantMembership:
        membership = TenantMembership(
            tenant_id=tenant_id, user_id=user_id, status=MembershipStatus.ACTIVE
        )
        self._session.add(membership)
        await self._session.flush()
        await self._session.refresh(membership)
        return membership

    async def remove(self, tenant_id: UUID, user_id: UUID) -> None:
        await self._session.execute(
            delete(TenantMembership).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        await self._session.flush()

    async def list_for_tenant(self, tenant_id: UUID) -> list[TenantMembership]:
        result = await self._session.execute(
            select(TenantMembership)
            .where(TenantMembership.tenant_id == tenant_id)
            .order_by(TenantMembership.joined_at.desc())
        )
        return list(result.scalars())
