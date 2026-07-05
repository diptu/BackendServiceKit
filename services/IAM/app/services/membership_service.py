"""MembershipService — user<->tenant membership."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import (
    TenantMembershipAlreadyExistsError,
    TenantMembershipNotFoundError,
)
from app.models.membership import TenantMembership
from app.repositories.membership import TenantMembershipRepository


class MembershipService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TenantMembershipRepository(session)

    async def add_member(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> TenantMembership:
        if await self._repo.exists(tenant_id, user_id):
            raise TenantMembershipAlreadyExistsError(tenant_id, user_id)
        return await self._repo.add(tenant_id, user_id)

    async def remove_member(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if not await self._repo.exists(tenant_id, user_id):
            raise TenantMembershipNotFoundError(tenant_id, user_id)
        await self._repo.remove(tenant_id, user_id)

    async def list_members(self, tenant_id: uuid.UUID) -> list[TenantMembership]:
        return await self._repo.list_for_tenant(tenant_id)
