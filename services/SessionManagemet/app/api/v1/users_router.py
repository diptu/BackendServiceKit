"""User-specific session endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.dependencies import SessionServiceDep, TenantIdDep
from app.api.v1.sessions_router import to_session_response
from app.schemas.session import RevokeAllResponse, SessionListResponse

router = APIRouter(prefix="/users", tags=["User Sessions"])


@router.get("/{user_id}/sessions", response_model=SessionListResponse)
async def list_user_sessions(
    user_id: UUID,
    tenant_id: TenantIdDep,
    svc: SessionServiceDep,
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


@router.delete("/{user_id}/sessions", response_model=RevokeAllResponse)
async def revoke_user_sessions(
    user_id: UUID, tenant_id: TenantIdDep, svc: SessionServiceDep
) -> RevokeAllResponse:
    revoked = await svc.revoke_all_for_user(tenant_id, user_id)
    return RevokeAllResponse(revoked=revoked)
