"""AuditEventService — read access to the authorization audit trail.

Recording happens inline in RoleService/GroupService/MembershipService/
EntitlementService (each owns its own AuditEventRepository) — this
service only serves the read side, GET /audit-events.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.repositories.audit_event import AuditEventRepository
from app.repositories.base import PageResult


class AuditEventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditEventRepository(session)

    async def list(
        self,
        *,
        tenant_id: uuid.UUID,
        subject_user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[AuditEvent]:
        return await self._repo.list_by_tenant(
            tenant_id,
            subject_user_id=subject_user_id,
            resource_type=resource_type,
            cursor=cursor,
            limit=limit,
        )
