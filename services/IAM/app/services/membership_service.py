"""MembershipService — user<->tenant membership."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditEventType
from app.domain.exceptions import (
    TenantMembershipAlreadyExistsError,
    TenantMembershipNotFoundError,
)
from app.models.membership import TenantMembership
from app.repositories.audit_event import AuditEventRepository
from app.repositories.membership import TenantMembershipRepository


class MembershipService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TenantMembershipRepository(session)
        self._audit_repo = AuditEventRepository(session)

    async def add_member(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> TenantMembership:
        if await self._repo.exists(tenant_id, user_id):
            raise TenantMembershipAlreadyExistsError(tenant_id, user_id)
        membership = await self._repo.add(tenant_id, user_id)
        await self._audit_repo.record(
            tenant_id=tenant_id,
            event_type=AuditEventType.TENANT_MEMBERSHIP_ADDED,
            resource_type="tenant_membership",
            subject_user_id=user_id,
            actor_id=actor_id,
        )
        return membership

    async def remove_member(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        if not await self._repo.exists(tenant_id, user_id):
            raise TenantMembershipNotFoundError(tenant_id, user_id)
        await self._repo.remove(tenant_id, user_id)
        await self._audit_repo.record(
            tenant_id=tenant_id,
            event_type=AuditEventType.TENANT_MEMBERSHIP_REMOVED,
            resource_type="tenant_membership",
            subject_user_id=user_id,
            actor_id=actor_id,
        )

    async def list_members(self, tenant_id: uuid.UUID) -> list[TenantMembership]:
        return await self._repo.list_for_tenant(tenant_id)
