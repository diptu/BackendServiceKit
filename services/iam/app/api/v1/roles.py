from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_async_db, get_current_user
from app.repositories.organization import OrganizationRepository
from app.repositories.role import RoleRepository
from app.schemas.role import (
    RoleCreate,
    RoleOut,
    RolePermissionsAssignRequest,
    RoleUpdate,
)
from app.schemas.user import UserOut
from app.services.role import RoleService

router = APIRouter(prefix="/roles", tags=["Role Management"])


def _get_service(db: AsyncSession = Depends(get_async_db)) -> RoleService:
    return RoleService(
        role_repo=RoleRepository(db),
        org_repo=OrganizationRepository(db),
    )


@router.get(
    "",
    response_model=list[RoleOut],
    summary="List roles (global roles, or one organization's custom + global roles)",
)
async def list_roles(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
    organization_id: Annotated[UUID | None, Query()] = None,
) -> list[RoleOut]:
    return await svc.list_roles(current_user, organization_id)


@router.post(
    "",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role (global: platform admin only; org-scoped: organizations:manage_roles)",
)
async def create_role(
    data: RoleCreate,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
) -> RoleOut:
    return await svc.create_role(data, current_user)


@router.get(
    "/{role_id}",
    response_model=RoleOut,
    summary="Get a role",
)
async def get_role(
    role_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
) -> RoleOut:
    return await svc.get_role(role_id, current_user)


@router.patch(
    "/{role_id}",
    response_model=RoleOut,
    summary="Update a role (system roles are immutable)",
)
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
) -> RoleOut:
    return await svc.update_role(role_id, data, current_user)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role (system roles are immutable; must not be in use)",
)
async def delete_role(
    role_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
) -> None:
    await svc.delete_role(role_id, current_user)


@router.post(
    "/{role_id}/permissions",
    response_model=RoleOut,
    summary="Assign one or more existing permissions to a role",
)
async def add_permissions(
    role_id: UUID,
    data: RolePermissionsAssignRequest,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
) -> RoleOut:
    return await svc.add_permissions(role_id, data.permission_slugs, current_user)


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleOut,
    summary="Remove a permission from a role",
)
async def remove_permission(
    role_id: UUID,
    permission_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[RoleService, Depends(_get_service)],
) -> RoleOut:
    return await svc.remove_permission(role_id, permission_id, current_user)
