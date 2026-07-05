"""Users CRUD + status lifecycle + status-history endpoints.

Implements every endpoint documented in services/UserManagement/README.md's
Users/Status sections (tenant_memberships is deliberately not implemented
here — already owned by IAM; see TODO.md).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import TenantIdDep, UserDep, UserServiceDep
from app.domain.commands import CreateUserCmd, UpdateUserCmd
from app.domain.exceptions import (
    InvalidUserStatusTransitionError,
    UserEmailConflictError,
    UserNotDeletedError,
    UserNotFoundError,
)
from app.schemas.status_history import (
    UserStatusHistoryListResponse,
    UserStatusHistoryResponse,
)
from app.schemas.user import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserStatusTransitionRequest,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest, tenant_id: TenantIdDep, svc: UserServiceDep
) -> UserResponse:
    cmd = CreateUserCmd(
        tenant_id=tenant_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
    )
    try:
        user = await svc.create(cmd)
    except UserEmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    tenant_id: TenantIdDep,
    svc: UserServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> UserListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user: UserDep) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user: UserDep, body: UpdateUserRequest, tenant_id: TenantIdDep, svc: UserServiceDep
) -> UserResponse:
    cmd = UpdateUserCmd(
        email=body.email, first_name=body.first_name, last_name=body.last_name
    )
    try:
        updated = await svc.update(user.id, tenant_id, cmd)
    except UserEmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(updated)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user: UserDep, tenant_id: TenantIdDep, svc: UserServiceDep
) -> None:
    await svc.delete(user.id, tenant_id)


@router.post("/{user_id}/restore", response_model=UserResponse)
async def restore_user(
    user_id: UUID, tenant_id: TenantIdDep, svc: UserServiceDep
) -> UserResponse:
    """Undo a soft-delete. Not routed through UserDep — a deleted user is
    excluded by that dependency's default lookup, which is exactly the
    case this endpoint needs to reach."""
    try:
        restored = await svc.restore(user_id, tenant_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UserNotDeletedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(restored)


# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user: UserDep,
    body: UserStatusTransitionRequest,
    tenant_id: TenantIdDep,
    svc: UserServiceDep,
) -> UserResponse:
    try:
        updated = await svc.activate(
            user.id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except InvalidUserStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(updated)


@router.post("/{user_id}/suspend", response_model=UserResponse)
async def suspend_user(
    user: UserDep,
    body: UserStatusTransitionRequest,
    tenant_id: TenantIdDep,
    svc: UserServiceDep,
) -> UserResponse:
    try:
        updated = await svc.suspend(
            user.id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except InvalidUserStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(updated)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user: UserDep,
    body: UserStatusTransitionRequest,
    tenant_id: TenantIdDep,
    svc: UserServiceDep,
) -> UserResponse:
    try:
        updated = await svc.deactivate(
            user.id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except InvalidUserStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UserResponse.model_validate(updated)


@router.get("/{user_id}/status-history", response_model=UserStatusHistoryListResponse)
async def get_user_status_history(
    user: UserDep,
    tenant_id: TenantIdDep,
    svc: UserServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> UserStatusHistoryListResponse:
    page = await svc.list_status_history(user.id, tenant_id, cursor=cursor, limit=limit)
    return UserStatusHistoryListResponse(
        items=[UserStatusHistoryResponse.model_validate(h) for h in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )
