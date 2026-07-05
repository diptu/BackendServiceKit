"""User lifecycle endpoints — mounted at /api/v1/user-lifecycle/{user_id}.

Not /api/v1/users/{user_id}/... as README.md literally shows — APIGateway's
/api/v1/users prefix already points at UserManagement, and its route
registry does plain string-prefix matching with no path templating. See
TODO.md.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import LifecycleServiceDep, TenantIdDep
from app.domain.exceptions import (
    InvalidLifecycleTransitionError,
    RemoteUserNotDeletedError,
    RemoteUserNotFoundError,
    UserManagementUnavailableError,
)
from app.schemas.lifecycle import (
    LifecycleEventListResponse,
    LifecycleEventResponse,
    LifecycleStateResponse,
    LifecycleStatusResponse,
    LockRequest,
    RemoteUserResponse,
    TransitionRequest,
)

router = APIRouter(prefix="/user-lifecycle/{user_id}", tags=["User Lifecycle"])


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, RemoteUserNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (InvalidLifecycleTransitionError, RemoteUserNotDeletedError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, UserManagementUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    raise exc


@router.post("/activate", response_model=LifecycleStateResponse)
async def activate(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.activate(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/onboard", response_model=LifecycleStateResponse)
async def onboard(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.onboard(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/deactivate", response_model=LifecycleStateResponse)
async def deactivate(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.deactivate(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/offboard", response_model=LifecycleStateResponse)
async def offboard(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.offboard(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/suspend", response_model=LifecycleStateResponse)
async def suspend(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.suspend(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/unsuspend", response_model=LifecycleStateResponse)
async def unsuspend(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.unsuspend(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/lock", response_model=LifecycleStateResponse)
async def lock(
    user_id: UUID, body: LockRequest, tenant_id: TenantIdDep, svc: LifecycleServiceDep
) -> LifecycleStateResponse:
    try:
        state = await svc.lock(
            user_id, tenant_id, reason=body.reason, locked_by=body.locked_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/unlock", response_model=LifecycleStateResponse)
async def unlock(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> LifecycleStateResponse:
    try:
        state = await svc.unlock(
            user_id, tenant_id, reason=body.reason, performed_by=body.performed_by
        )
    except (
        RemoteUserNotFoundError,
        InvalidLifecycleTransitionError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return LifecycleStateResponse.model_validate(state)


@router.post("/restore", response_model=RemoteUserResponse)
async def restore(
    user_id: UUID,
    body: TransitionRequest,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
) -> RemoteUserResponse:
    try:
        restored = await svc.restore(user_id, tenant_id, performed_by=body.performed_by)
    except (
        RemoteUserNotFoundError,
        RemoteUserNotDeletedError,
        UserManagementUnavailableError,
    ) as exc:
        raise _handle(exc) from exc
    return RemoteUserResponse.model_validate(restored)


@router.get("/status", response_model=LifecycleStatusResponse)
async def get_status(
    user_id: UUID, tenant_id: TenantIdDep, svc: LifecycleServiceDep
) -> LifecycleStatusResponse:
    try:
        view = await svc.get_status(user_id, tenant_id)
    except (RemoteUserNotFoundError, UserManagementUnavailableError) as exc:
        raise _handle(exc) from exc
    return LifecycleStatusResponse(
        user_id=view.user_id,
        tenant_id=view.tenant_id,
        email=view.email,
        display_name=view.display_name,
        remote_status=view.remote_status,
        lifecycle_status=view.lifecycle_status,
        deleted_at=view.deleted_at,
        locked_reason=view.locked_reason,
        locked_by=view.locked_by,
        last_event_type=view.last_event.event_type if view.last_event else None,
        last_event_at=view.last_event.occurred_at if view.last_event else None,
    )


@router.get("/events", response_model=LifecycleEventListResponse)
async def list_events(
    user_id: UUID,
    tenant_id: TenantIdDep,
    svc: LifecycleServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> LifecycleEventListResponse:
    page = await svc.list_events(user_id, cursor=cursor, limit=limit)
    return LifecycleEventListResponse(
        items=[LifecycleEventResponse.model_validate(e) for e in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )
