"""Tenant lifecycle state machine endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import DbDep
from app.domain.exceptions import (
    InvalidLifecycleTransitionError,
    TenantLifecycleAlreadyExistsError,
    TenantLifecycleNotFoundError,
)
from app.schemas.lifecycle import (
    LifecycleEventResponse,
    LifecycleHistoryResponse,
    LifecycleStateResponse,
    TransitionRequest,
)
from app.services.lifecycle_service import TenantLifecycleService

router = APIRouter(prefix="/lifecycle", tags=["Lifecycle"])


def _svc(db: AsyncSession) -> TenantLifecycleService:
    return TenantLifecycleService(db)


@router.get("/{tenant_id}", response_model=LifecycleStateResponse)
async def get_lifecycle_state(tenant_id: UUID, db: DbDep) -> LifecycleStateResponse:
    try:
        state = await _svc(db).get_state(tenant_id)
    except TenantLifecycleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/provision", response_model=LifecycleStateResponse)
async def provision(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).provision(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except TenantLifecycleAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/pend", response_model=LifecycleStateResponse)
async def pend(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).pend(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/activate", response_model=LifecycleStateResponse)
async def activate(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).activate(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/suspend", response_model=LifecycleStateResponse)
async def suspend(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).suspend(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/reactivate", response_model=LifecycleStateResponse)
async def reactivate(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).reactivate(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/lock", response_model=LifecycleStateResponse)
async def lock(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).lock(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/unlock", response_model=LifecycleStateResponse)
async def unlock(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).unlock(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/archive", response_model=LifecycleStateResponse)
async def archive(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).archive(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.put("/{tenant_id}/delete", response_model=LifecycleStateResponse)
async def delete(
    tenant_id: UUID, body: TransitionRequest, db: DbDep
) -> LifecycleStateResponse:
    try:
        state = await _svc(db).delete(
            tenant_id,
            reason=body.reason,
            performed_by=body.performed_by,
            source=body.source,
        )
    except (TenantLifecycleNotFoundError, InvalidLifecycleTransitionError) as exc:
        code = 404 if isinstance(exc, TenantLifecycleNotFoundError) else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return LifecycleStateResponse.model_validate(state)


@router.get("/{tenant_id}/history", response_model=LifecycleHistoryResponse)
async def get_history(
    tenant_id: UUID,
    db: DbDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> LifecycleHistoryResponse:
    svc = _svc(db)
    try:
        state = await svc.get_state(tenant_id)
    except TenantLifecycleNotFoundError:
        state = None

    page = await svc.get_history(tenant_id, cursor=cursor, limit=limit)
    return LifecycleHistoryResponse(
        tenant_id=tenant_id,
        current_status=state.current_status if state else None,
        events=[LifecycleEventResponse.model_validate(e) for e in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )
