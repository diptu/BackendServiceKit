"""Session lifecycle & information endpoints.

Route order matters: the static `/sessions/me` and `/sessions/revoke-all` are
declared before the dynamic `/sessions/{session_id}` so they are not captured
as a session_id.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.dependencies import (
    SessionServiceDep,
    SessionTokenDep,
    TenantIdDep,
)
from app.domain.commands import CreateSessionCmd
from app.models.session import Session
from app.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    RevokeAllRequest,
    RevokeAllResponse,
    SessionListResponse,
    SessionResponse,
)
from app.services.session_service import session_status

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        status=session_status(session).value,
        device_info=session.device_info,
        ip_address=session.ip_address,
        user_agent=session.user_agent,
        created_at=session.created_at,
        last_seen_at=session.last_seen_at,
        expires_at=session.expires_at,
        revoked_at=session.revoked_at,
    )


@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest, tenant_id: TenantIdDep, svc: SessionServiceDep
) -> CreateSessionResponse:
    cmd = CreateSessionCmd(
        user_id=body.user_id,
        device_info=body.device_info,
        ip_address=body.ip_address,
        user_agent=body.user_agent,
        ttl_seconds=body.ttl_seconds,
    )
    created = await svc.create(tenant_id, cmd)
    return CreateSessionResponse(
        session_token=created.raw_token,
        session=to_session_response(created.session),
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    tenant_id: TenantIdDep,
    svc: SessionServiceDep,
    user_id: UUID | None = None,
    active_only: bool = False,
    cursor: str | None = None,
    limit: int = 20,
) -> SessionListResponse:
    page = await svc.list(
        tenant_id,
        user_id=user_id,
        active_only=active_only,
        cursor=cursor,
        limit=limit,
    )
    return SessionListResponse(
        items=[to_session_response(s) for s in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/me", response_model=SessionResponse)
async def current_session(
    tenant_id: TenantIdDep, token: SessionTokenDep, svc: SessionServiceDep
) -> SessionResponse:
    """Resolve the caller's own session from the X-Session-Token header."""
    session = await svc.resolve_by_token(tenant_id, token)
    return to_session_response(session)


@router.post("/revoke-all", response_model=RevokeAllResponse)
async def revoke_all(
    body: RevokeAllRequest, tenant_id: TenantIdDep, svc: SessionServiceDep
) -> RevokeAllResponse:
    revoked = await svc.revoke_all_for_user(tenant_id, body.user_id)
    return RevokeAllResponse(revoked=revoked)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID, tenant_id: TenantIdDep, svc: SessionServiceDep
) -> SessionResponse:
    session = await svc.get(tenant_id, session_id)
    return to_session_response(session)


@router.delete("/{session_id}", status_code=204)
async def revoke_session(
    session_id: UUID, tenant_id: TenantIdDep, svc: SessionServiceDep
) -> None:
    await svc.revoke(tenant_id, session_id)


@router.post("/{session_id}/refresh", response_model=SessionResponse)
async def refresh_session(
    session_id: UUID, tenant_id: TenantIdDep, svc: SessionServiceDep
) -> SessionResponse:
    session = await svc.refresh(tenant_id, session_id)
    return to_session_response(session)
