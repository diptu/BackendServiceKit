"""Roles CRUD + role<->permission linkage + user<->role assignment.

Implements the Roles, Permissions-on-a-role, and User Roles sections of
services/IAM/README.md's API Reference.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import RoleDep, RoleServiceDep, TenantIdDep
from app.domain.commands import CreateRoleCmd, UpdateRoleCmd
from app.domain.exceptions import (
    PermissionNotFoundError,
    RoleNameConflictError,
    RolePermissionAlreadyAssignedError,
    RolePermissionNotAssignedError,
    UserRoleAlreadyAssignedError,
    UserRoleNotAssignedError,
)
from app.schemas.permission import PermissionResponse
from app.schemas.role import (
    AssignPermissionRequest,
    AssignRoleRequest,
    CreateRoleRequest,
    RoleListResponse,
    RolePermissionListResponse,
    RoleResponse,
    UpdateRoleRequest,
)

router = APIRouter(tags=["Roles"])


# ---------------------------------------------------------------------------
# Role CRUD
# ---------------------------------------------------------------------------


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(
    body: CreateRoleRequest, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> RoleResponse:
    cmd = CreateRoleCmd(
        tenant_id=tenant_id, name=body.name, description=body.description
    )
    try:
        role = await svc.create(cmd)
    except RoleNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RoleResponse.model_validate(role)


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    tenant_id: TenantIdDep,
    svc: RoleServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> RoleListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return RoleListResponse(
        items=[RoleResponse.model_validate(r) for r in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(role: RoleDep) -> RoleResponse:
    return RoleResponse.model_validate(role)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role: RoleDep, body: UpdateRoleRequest, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> RoleResponse:
    cmd = UpdateRoleCmd(name=body.name, description=body.description)
    try:
        updated = await svc.update(role.id, tenant_id, cmd)
    except RoleNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RoleResponse.model_validate(updated)


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
    role: RoleDep, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> None:
    await svc.delete(role.id, tenant_id)


# ---------------------------------------------------------------------------
# Role <-> Permission linkage
# ---------------------------------------------------------------------------


@router.get("/roles/{role_id}/permissions", response_model=RolePermissionListResponse)
async def list_role_permissions(
    role: RoleDep, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> RolePermissionListResponse:
    permissions = await svc.list_permissions(role.id, tenant_id)
    return RolePermissionListResponse(
        items=[PermissionResponse.model_validate(p) for p in permissions],
        total=len(permissions),
    )


@router.post("/roles/{role_id}/permissions", status_code=204)
async def add_role_permission(
    role: RoleDep,
    body: AssignPermissionRequest,
    tenant_id: TenantIdDep,
    svc: RoleServiceDep,
) -> None:
    try:
        await svc.add_permission(role.id, body.permission_id, tenant_id)
    except PermissionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RolePermissionAlreadyAssignedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204)
async def remove_role_permission(
    role: RoleDep, permission_id: UUID, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> None:
    try:
        await svc.remove_permission(role.id, permission_id, tenant_id)
    except RolePermissionNotAssignedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# User <-> Role assignment
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}/roles", response_model=RoleListResponse)
async def list_user_roles(
    user_id: UUID, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> RoleListResponse:
    roles = await svc.list_roles_for_user(user_id, tenant_id)
    return RoleListResponse(
        items=[RoleResponse.model_validate(r) for r in roles],
        total=len(roles),
        has_more=False,
    )


@router.post("/users/{user_id}/roles", status_code=204)
async def assign_user_role(
    user_id: UUID,
    body: AssignRoleRequest,
    tenant_id: TenantIdDep,
    svc: RoleServiceDep,
) -> None:
    try:
        await svc.assign_to_user(user_id, body.role_id, tenant_id)
    except UserRoleAlreadyAssignedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def unassign_user_role(
    user_id: UUID, role_id: UUID, tenant_id: TenantIdDep, svc: RoleServiceDep
) -> None:
    try:
        await svc.unassign_from_user(user_id, role_id, tenant_id)
    except UserRoleNotAssignedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
