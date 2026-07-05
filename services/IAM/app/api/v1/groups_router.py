"""Groups CRUD + group<->user membership.

Implements the Groups section of services/IAM/README.md's API Reference.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import GroupDep, GroupServiceDep, TenantIdDep
from app.domain.commands import CreateGroupCmd, UpdateGroupCmd
from app.domain.exceptions import (
    GroupMembershipAlreadyExistsError,
    GroupMembershipNotFoundError,
    GroupNameConflictError,
)
from app.schemas.common import UserIdListResponse
from app.schemas.group import (
    AddGroupMemberRequest,
    CreateGroupRequest,
    GroupListResponse,
    GroupResponse,
    UpdateGroupRequest,
)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    body: CreateGroupRequest, tenant_id: TenantIdDep, svc: GroupServiceDep
) -> GroupResponse:
    cmd = CreateGroupCmd(
        tenant_id=tenant_id, name=body.name, description=body.description
    )
    try:
        group = await svc.create(cmd)
    except GroupNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return GroupResponse.model_validate(group)


@router.get("", response_model=GroupListResponse)
async def list_groups(
    tenant_id: TenantIdDep,
    svc: GroupServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> GroupListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return GroupListResponse(
        items=[GroupResponse.model_validate(g) for g in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group: GroupDep) -> GroupResponse:
    return GroupResponse.model_validate(group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group: GroupDep,
    body: UpdateGroupRequest,
    tenant_id: TenantIdDep,
    svc: GroupServiceDep,
) -> GroupResponse:
    cmd = UpdateGroupCmd(name=body.name, description=body.description)
    try:
        updated = await svc.update(group.id, tenant_id, cmd)
    except GroupNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return GroupResponse.model_validate(updated)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group: GroupDep, tenant_id: TenantIdDep, svc: GroupServiceDep
) -> None:
    await svc.delete(group.id, tenant_id)


# ---------------------------------------------------------------------------
# Group <-> User membership
# ---------------------------------------------------------------------------


@router.get("/{group_id}/members", response_model=UserIdListResponse)
async def list_group_members(
    group: GroupDep, tenant_id: TenantIdDep, svc: GroupServiceDep
) -> UserIdListResponse:
    member_ids = await svc.list_members(group.id, tenant_id)
    return UserIdListResponse(items=member_ids, total=len(member_ids))


@router.post("/{group_id}/members", status_code=204)
async def add_group_member(
    group: GroupDep,
    body: AddGroupMemberRequest,
    tenant_id: TenantIdDep,
    svc: GroupServiceDep,
) -> None:
    try:
        await svc.add_member(group.id, body.user_id, tenant_id)
    except GroupMembershipAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_group_member(
    group: GroupDep, user_id: UUID, tenant_id: TenantIdDep, svc: GroupServiceDep
) -> None:
    try:
        await svc.remove_member(group.id, user_id, tenant_id)
    except GroupMembershipNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
