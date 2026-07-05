"""Entitlements — what a user is granted.

Implements the Entitlements section of services/IAM/README.md's API
Reference. README only documents list/create; detail+delete are added for
CRUD symmetry with every other resource in this service.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.dependencies import EntitlementServiceDep, TenantIdDep
from app.domain.commands import CreateEntitlementCmd
from app.schemas.entitlement import (
    CreateEntitlementRequest,
    EntitlementListResponse,
    EntitlementResponse,
)

router = APIRouter(prefix="/entitlements", tags=["Entitlements"])


@router.post("", response_model=EntitlementResponse, status_code=201)
async def create_entitlement(
    body: CreateEntitlementRequest, tenant_id: TenantIdDep, svc: EntitlementServiceDep
) -> EntitlementResponse:
    cmd = CreateEntitlementCmd(
        tenant_id=tenant_id, user_id=body.user_id, key=body.key, value=body.value
    )
    entitlement = await svc.create(cmd)
    return EntitlementResponse.model_validate(entitlement)


@router.get("", response_model=EntitlementListResponse)
async def list_entitlements(
    tenant_id: TenantIdDep,
    svc: EntitlementServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> EntitlementListResponse:
    page = await svc.list(tenant_id=tenant_id, cursor=cursor, limit=limit)
    return EntitlementListResponse(
        items=[EntitlementResponse.model_validate(e) for e in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{entitlement_id}", response_model=EntitlementResponse)
async def get_entitlement(
    entitlement_id: UUID, tenant_id: TenantIdDep, svc: EntitlementServiceDep
) -> EntitlementResponse:
    entitlement = await svc.get(entitlement_id, tenant_id)
    return EntitlementResponse.model_validate(entitlement)


@router.delete("/{entitlement_id}", status_code=204)
async def delete_entitlement(
    entitlement_id: UUID, tenant_id: TenantIdDep, svc: EntitlementServiceDep
) -> None:
    await svc.delete(entitlement_id, tenant_id)
