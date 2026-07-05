"""User Attributes — ABAC key/value data.

Implements the Attributes section of services/IAM/README.md's API Reference.

Mounted at /user-attributes/{user_id}, not the literal /users/{user_id}/attributes
from the README — APIGateway's /api/v1/users prefix now points at
UserManagement (the authoritative user CRUD service), and its route
registry does plain string-prefix matching with no path templating, so a
nested /users/{user_id}/attributes path would also be swallowed by that
prefix. Same rename precedent as IAM's own tenant-memberships route. See
services/UserManagement/TODO.md.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.v1.dependencies import AttributeServiceDep, TenantIdDep
from app.domain.commands import CreateAttributeCmd, UpdateAttributeCmd
from app.domain.exceptions import AttributeKeyConflictError
from app.schemas.attribute import (
    AttributeListResponse,
    AttributeResponse,
    CreateAttributeRequest,
    UpdateAttributeRequest,
)

router = APIRouter(prefix="/user-attributes/{user_id}", tags=["Attributes"])


@router.get("", response_model=AttributeListResponse)
async def list_attributes(
    user_id: UUID, tenant_id: TenantIdDep, svc: AttributeServiceDep
) -> AttributeListResponse:
    attributes = await svc.list_for_user(user_id, tenant_id)
    return AttributeListResponse(
        items=[AttributeResponse.model_validate(a) for a in attributes],
        total=len(attributes),
    )


@router.post("", response_model=AttributeResponse, status_code=201)
async def create_attribute(
    user_id: UUID,
    body: CreateAttributeRequest,
    tenant_id: TenantIdDep,
    svc: AttributeServiceDep,
) -> AttributeResponse:
    cmd = CreateAttributeCmd(
        tenant_id=tenant_id,
        user_id=user_id,
        key=body.key,
        value=body.value,
        value_type=body.value_type,
    )
    try:
        attribute = await svc.create(cmd)
    except AttributeKeyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AttributeResponse.model_validate(attribute)


@router.patch("/{attribute_id}", response_model=AttributeResponse)
async def update_attribute(
    user_id: UUID,
    attribute_id: UUID,
    body: UpdateAttributeRequest,
    tenant_id: TenantIdDep,
    svc: AttributeServiceDep,
) -> AttributeResponse:
    cmd = UpdateAttributeCmd(value=body.value, value_type=body.value_type)
    updated = await svc.update(attribute_id, user_id, tenant_id, cmd)
    return AttributeResponse.model_validate(updated)


@router.delete("/{attribute_id}", status_code=204)
async def delete_attribute(
    user_id: UUID, attribute_id: UUID, tenant_id: TenantIdDep, svc: AttributeServiceDep
) -> None:
    await svc.delete(attribute_id, user_id, tenant_id)
