from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_async_db, get_current_user
from app.repositories.organization import OrganizationRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.organization import (
    MemberAddRequest,
    MemberRoleUpdateRequest,
    OrganizationCreate,
    OrganizationDetailOut,
    OrganizationMemberOut,
    OrganizationPageResponse,
    OrganizationUpdate,
)
from app.schemas.user import UserOut
from app.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organization Management"])


def _get_service(db: AsyncSession = Depends(get_async_db)) -> OrganizationService:
    return OrganizationService(
        org_repo=OrganizationRepository(db),
        role_repo=RoleRepository(db),
        user_repo=UserRepository(db),
    )


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=OrganizationDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization (creator becomes owner)",
)
async def create_organization(
    data: OrganizationCreate,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> OrganizationDetailOut:
    return await svc.create_organization(current_user, data)


@router.get(
    "",
    response_model=OrganizationPageResponse,
    summary="List organizations the caller belongs to (or all, for superusers)",
)
async def list_organizations(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OrganizationPageResponse:
    return await svc.list_organizations(current_user, page=page, page_size=page_size)


@router.get(
    "/{organization_id}",
    response_model=OrganizationDetailOut,
    summary="Get an organization (members only)",
)
async def get_organization(
    organization_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> OrganizationDetailOut:
    return await svc.get_organization(organization_id, current_user)


@router.patch(
    "/{organization_id}",
    response_model=OrganizationDetailOut,
    summary="Update an organization (requires organizations:update)",
)
async def update_organization(
    organization_id: UUID,
    data: OrganizationUpdate,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> OrganizationDetailOut:
    return await svc.update_organization(organization_id, data, current_user)


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization (requires organizations:delete)",
)
async def delete_organization(
    organization_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> None:
    await svc.delete_organization(organization_id, current_user)


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberOut],
    summary="List members of an organization",
)
async def list_members(
    organization_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> list[OrganizationMemberOut]:
    return await svc.list_members(organization_id, current_user)


@router.post(
    "/{organization_id}/members",
    response_model=OrganizationMemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member (requires organizations:manage_members)",
)
async def add_member(
    organization_id: UUID,
    data: MemberAddRequest,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> OrganizationMemberOut:
    return await svc.add_member(organization_id, data, current_user)


@router.patch(
    "/{organization_id}/members/{user_id}",
    response_model=OrganizationMemberOut,
    summary="Change a member's role (requires organizations:manage_members)",
)
async def update_member_role(
    organization_id: UUID,
    user_id: UUID,
    data: MemberRoleUpdateRequest,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> OrganizationMemberOut:
    return await svc.update_member_role(organization_id, user_id, data, current_user)


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member (self-removal allowed; otherwise requires organizations:manage_members)",
)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    svc: Annotated[OrganizationService, Depends(_get_service)],
) -> None:
    await svc.remove_member(organization_id, user_id, current_user)
