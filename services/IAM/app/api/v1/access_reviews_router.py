"""Access Reviews — access-governance review lifecycle.

Not in services/IAM/README.md's endpoint table, but in root CLAUDE.md's
ownership list. Minimal create/list/detail/record-decision shape.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.dependencies import AccessReviewServiceDep, TenantIdDep
from app.domain.commands import CreateAccessReviewCmd, UpdateAccessReviewCmd
from app.schemas.access_review import (
    AccessReviewListResponse,
    AccessReviewResponse,
    CreateAccessReviewRequest,
    RecordAccessReviewDecisionRequest,
)

router = APIRouter(prefix="/access-reviews", tags=["Access Reviews"])


@router.post("", response_model=AccessReviewResponse, status_code=201)
async def create_access_review(
    body: CreateAccessReviewRequest, tenant_id: TenantIdDep, svc: AccessReviewServiceDep
) -> AccessReviewResponse:
    cmd = CreateAccessReviewCmd(
        tenant_id=tenant_id,
        subject_user_id=body.subject_user_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        reviewer_id=body.reviewer_id,
    )
    access_review = await svc.create(cmd)
    return AccessReviewResponse.model_validate(access_review)


@router.get("", response_model=AccessReviewListResponse)
async def list_access_reviews(
    tenant_id: TenantIdDep,
    svc: AccessReviewServiceDep,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> AccessReviewListResponse:
    page = await svc.list(tenant_id=tenant_id, cursor=cursor, limit=limit)
    return AccessReviewListResponse(
        items=[AccessReviewResponse.model_validate(a) for a in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/{access_review_id}", response_model=AccessReviewResponse)
async def get_access_review(
    access_review_id: UUID, tenant_id: TenantIdDep, svc: AccessReviewServiceDep
) -> AccessReviewResponse:
    access_review = await svc.get(access_review_id, tenant_id)
    return AccessReviewResponse.model_validate(access_review)


@router.patch("/{access_review_id}", response_model=AccessReviewResponse)
async def record_access_review_decision(
    access_review_id: UUID,
    body: RecordAccessReviewDecisionRequest,
    tenant_id: TenantIdDep,
    svc: AccessReviewServiceDep,
) -> AccessReviewResponse:
    cmd = UpdateAccessReviewCmd(
        status=body.status,
        decision_notes=body.decision_notes,
        reviewer_id=body.reviewer_id,
    )
    updated = await svc.record_decision(access_review_id, tenant_id, cmd)
    return AccessReviewResponse.model_validate(updated)
