"""Permissions CRUD.

Implements the Permissions section of services/IAM/README.md's API Reference.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import PermissionDep, PermissionServiceDep, TenantIdDep
from app.domain.commands import CreatePermissionCmd, UpdatePermissionCmd
from app.domain.exceptions import PermissionNameConflictError
from app.schemas.permission import (
    CreatePermissionRequest,
    PermissionListResponse,
    PermissionResponse,
    UpdatePermissionRequest,
)

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.post("", response_model=PermissionResponse, status_code=201)
async def create_permission(
    body: CreatePermissionRequest, tenant_id: TenantIdDep, svc: PermissionServiceDep
) -> PermissionResponse:
    cmd = CreatePermissionCmd(
        tenant_id=tenant_id, name=body.name, description=body.description
    )
    try:
        permission = await svc.create(cmd)
    except PermissionNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PermissionResponse.model_validate(permission)


@router.get("", response_model=PermissionListResponse)
async def list_permissions(
    tenant_id: TenantIdDep,
    svc: PermissionServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> PermissionListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return PermissionListResponse(
        items=[PermissionResponse.model_validate(p) for p in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(permission: PermissionDep) -> PermissionResponse:
    return PermissionResponse.model_validate(permission)


@router.patch("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission: PermissionDep,
    body: UpdatePermissionRequest,
    tenant_id: TenantIdDep,
    svc: PermissionServiceDep,
) -> PermissionResponse:
    cmd = UpdatePermissionCmd(name=body.name, description=body.description)
    try:
        updated = await svc.update(permission.id, tenant_id, cmd)
    except PermissionNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PermissionResponse.model_validate(updated)


@router.delete("/{permission_id}", status_code=204)
async def delete_permission(
    permission: PermissionDep, tenant_id: TenantIdDep, svc: PermissionServiceDep
) -> None:
    await svc.delete(permission.id, tenant_id)
