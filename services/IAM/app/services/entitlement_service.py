"""EntitlementService — user-scoped entitlement CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import CreateEntitlementCmd
from app.domain.enums import AuditEventType, EntitlementStatus
from app.domain.exceptions import EntitlementNotFoundError
from app.models.entitlement import Entitlement
from app.repositories.audit_event import AuditEventRepository
from app.repositories.base import PageResult
from app.repositories.entitlement import EntitlementFilter, EntitlementRepository


class EntitlementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EntitlementRepository(session)
        self._audit_repo = AuditEventRepository(session)

    async def create(
        self, cmd: CreateEntitlementCmd, *, actor_id: uuid.UUID | None = None
    ) -> Entitlement:
        entitlement = Entitlement(
            id=uuid.uuid4(),
            tenant_id=cmd.tenant_id,
            user_id=cmd.user_id,
            key=cmd.key,
            value=cmd.value,
            status=EntitlementStatus.ACTIVE,
        )
        created = await self._repo.create(entitlement)
        await self._audit_repo.record(
            tenant_id=cmd.tenant_id,
            event_type=AuditEventType.ENTITLEMENT_GRANTED,
            resource_type="entitlement",
            resource_id=created.id,
            subject_user_id=cmd.user_id,
            actor_id=actor_id,
            details={"key": cmd.key},
        )
        return created

    async def get(self, entitlement_id: uuid.UUID, tenant_id: uuid.UUID) -> Entitlement:
        entitlement = await self._repo.get_by_id(entitlement_id, tenant_id=tenant_id)
        if entitlement is None:
            raise EntitlementNotFoundError(entitlement_id)
        return entitlement

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[Entitlement]:
        filters = EntitlementFilter(tenant_id=tenant_id)
        return await self._repo.list(filters=filters, cursor=cursor, limit=limit)

    async def delete(
        self,
        entitlement_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> None:
        entitlement = await self.get(entitlement_id, tenant_id)
        if entitlement.deleted_at is not None:
            return
        await self._repo.soft_delete(entitlement)
        await self._audit_repo.record(
            tenant_id=tenant_id,
            event_type=AuditEventType.ENTITLEMENT_REVOKED,
            resource_type="entitlement",
            resource_id=entitlement_id,
            subject_user_id=entitlement.user_id,
            actor_id=actor_id,
            details={"key": entitlement.key},
        )
