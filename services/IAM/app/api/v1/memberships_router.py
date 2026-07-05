"""Tenant Memberships — a user's membership within a tenant.

Implements the Tenant Memberships section of services/IAM/README.md's API
Reference, at `/tenant-memberships/{tenant_id}/members` rather than the
README's literal `/tenants/{tenant_id}/members` — APIGateway's route
registry does plain string-prefix matching with no path templating, and
Tenent already owns the `/api/v1/tenants` prefix for its own tenant CRUD.
Any request under `/api/v1/tenants/...` would match Tenent's rule first and
never reach IAM. See services/IAM/TODO.md.

Unlike every other router in this service, tenant_id here comes from the
URL path segment itself, not the X-Tenant-ID header.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.v1.dependencies import MembershipServiceDep
from app.domain.exceptions import (
    TenantMembershipAlreadyExistsError,
    TenantMembershipNotFoundError,
)
from app.schemas.membership import (
    AddTenantMemberRequest,
    TenantMembershipListResponse,
    TenantMembershipResponse,
)

router = APIRouter(
    prefix="/tenant-memberships/{tenant_id}/members", tags=["Tenant Memberships"]
)


@router.get("", response_model=TenantMembershipListResponse)
async def list_tenant_members(
    tenant_id: UUID, svc: MembershipServiceDep
) -> TenantMembershipListResponse:
    members = await svc.list_members(tenant_id)
    return TenantMembershipListResponse(
        items=[TenantMembershipResponse.model_validate(m) for m in members],
        total=len(members),
    )


@router.post("", response_model=TenantMembershipResponse, status_code=201)
async def add_tenant_member(
    tenant_id: UUID, body: AddTenantMemberRequest, svc: MembershipServiceDep
) -> TenantMembershipResponse:
    try:
        membership = await svc.add_member(tenant_id, body.user_id)
    except TenantMembershipAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TenantMembershipResponse.model_validate(membership)


@router.delete("/{user_id}", status_code=204)
async def remove_tenant_member(
    tenant_id: UUID, user_id: UUID, svc: MembershipServiceDep
) -> None:
    try:
        await svc.remove_member(tenant_id, user_id)
    except TenantMembershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
