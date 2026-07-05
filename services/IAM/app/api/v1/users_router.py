"""Users — read-only endpoints against the User Service projection.

No write endpoints: UserProjection is populated only by the (deferred)
user.created/updated/deleted event consumer. See services/IAM/TODO.md.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.dependencies import TenantIdDep, UserServiceDep
from app.schemas.user_projection import (
    UserProjectionListResponse,
    UserProjectionResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserProjectionListResponse)
async def list_users(
    tenant_id: TenantIdDep,
    svc: UserServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> UserProjectionListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return UserProjectionListResponse(
        items=[UserProjectionResponse.model_validate(u) for u in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{user_id}", response_model=UserProjectionResponse)
async def get_user(
    user_id: UUID, tenant_id: TenantIdDep, svc: UserServiceDep
) -> UserProjectionResponse:
    user = await svc.get(user_id, tenant_id)
    return UserProjectionResponse.model_validate(user)
