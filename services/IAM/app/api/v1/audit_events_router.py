"""Audit Events — the authorization audit trail.

Records every role assignment, role<->permission linkage change, group
membership change, tenant membership change, and entitlement grant/revoke
in this service. See app/models/audit_event.py for scope and the
actor_id-is-unverified caveat.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.dependencies import AuditEventServiceDep, TenantIdDep
from app.schemas.audit_event import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["Audit Events"])


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    tenant_id: TenantIdDep,
    svc: AuditEventServiceDep,
    subject_user_id: UUID | None = Query(None),
    resource_type: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> AuditEventListResponse:
    page = await svc.list(
        tenant_id=tenant_id,
        subject_user_id=subject_user_id,
        resource_type=resource_type,
        cursor=cursor,
        limit=limit,
    )
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(e) for e in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )
