"""Isolation REST endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGINATION_LIMIT, MAX_PAGINATION_LIMIT
from app.core.openapi import RESPONSES_READ, RESPONSES_WRITE
from app.dependencies.isolation import PolicyDep
from app.infrastructure.database.dependencies import get_db
from app.middleware.auth import verify_token
from app.middleware.rate_limit import limiter
from app.schemas.isolation import (
    BulkClaimRequest,
    CheckAccessRequest,
    CheckAccessResponse,
    DecisionListResponse,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdateRequest,
    ReleaseClaimRequest,
    ResolveContextRequest,
    ResolveContextResponse,
    ResourceClaimRequest,
    ResourceClaimResponse,
    ValidateQueryRequest,
    ValidateQueryResponse,
    ValidateRequest,
    ValidateResourceRequest,
    ValidateResourceResponse,
    ValidateResponse,
)
from app.services.isolation_service import IsolationService
from app.services.resource_claim_service import ResourceClaimService

if TYPE_CHECKING:
    from app.models.isolation_policy import IsolationPolicy
    from app.models.resource_claim import ResourceClaim

router = APIRouter(
    prefix="/isolation",
    tags=["Isolation"],
    dependencies=[Depends(verify_token)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _iso_svc(db: DbDep, request: Request) -> IsolationService:
    publisher: Any = getattr(request.app.state, "publisher", None)
    return IsolationService(db, publisher=publisher)


def _claim_svc(db: DbDep, request: Request) -> ResourceClaimService:
    publisher: Any = getattr(request.app.state, "publisher", None)
    return ResourceClaimService(db, publisher=publisher)


IsoSvcDep = Annotated[IsolationService, Depends(_iso_svc)]
ClaimSvcDep = Annotated[ResourceClaimService, Depends(_claim_svc)]


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate resource ownership for a batch of resource IDs",
)
@limiter.limit("200/minute")
async def validate(
    request: Request,
    body: ValidateRequest,
    svc: IsoSvcDep,
) -> ValidateResponse:
    return await svc.validate(
        body.caller_tenant_id,
        body.resource_ids,
        str(body.resource_type),
    )


@router.post(
    "/check-access",
    response_model=CheckAccessResponse,
    summary="Check access for a specific resource and action",
)
@limiter.limit("500/minute")
async def check_access(
    request: Request,
    body: CheckAccessRequest,
    svc: IsoSvcDep,
) -> CheckAccessResponse:
    from app.infrastructure.cache.redis_cache import (
        cache_get,
        cache_set,
        decision_cache_key,
    )
    from app.core.constants import CACHE_TTL_ALLOW_DECISION, CACHE_TTL_DENY_DECISION
    from app.domain.enums import IsolationDecision

    dkey = decision_cache_key(
        str(body.caller_tenant_id),
        str(body.target_tenant_id),
        body.resource_id,
        str(body.resource_type),
        str(body.action),
    )
    cached = await cache_get(dkey)
    if cached is not None:
        return CheckAccessResponse(**cached)

    request_id = getattr(request.state, "request_id", None)
    resp = await svc.check_access(
        body.caller_tenant_id,
        body.target_tenant_id,
        body.resource_id,
        str(body.resource_type),
        str(body.action),
        request_id=request_id,
    )

    ttl = (
        CACHE_TTL_ALLOW_DECISION
        if resp.decision == IsolationDecision.ALLOW
        else CACHE_TTL_DENY_DECISION
    )
    await cache_set(dkey, resp.model_dump(mode="json"), ttl=ttl)
    return resp


@router.post(
    "/resolve-context",
    response_model=ResolveContextResponse,
    summary="Extract tenant context from a JWT bearer token",
)
async def resolve_context(
    body: ResolveContextRequest,
    svc: IsoSvcDep,
) -> ResolveContextResponse:
    return await svc.resolve_context(body.token)


@router.post(
    "/validate-resource",
    response_model=ValidateResourceResponse,
    summary="Check ownership of a single resource",
)
async def validate_resource(
    body: ValidateResourceRequest,
    svc: IsoSvcDep,
    request: Request,
) -> ValidateResourceResponse:
    from app.infrastructure.cache.redis_cache import cache_get, cache_set, claim_cache_key
    from app.core.constants import CACHE_TTL_CLAIM
    from app.domain.enums import IsolationDecision

    ckey = claim_cache_key(str(body.resource_type), body.resource_id)
    cached = await cache_get(ckey)
    if cached is not None:
        return ValidateResourceResponse(**cached)

    resp = await svc.validate_resource(
        body.caller_tenant_id,
        body.resource_id,
        str(body.resource_type),
    )

    if resp.decision == IsolationDecision.ALLOW:
        await cache_set(ckey, resp.model_dump(mode="json"), ttl=CACHE_TTL_CLAIM)
    return resp


@router.post(
    "/validate-query",
    response_model=ValidateQueryResponse,
    summary="Validate that a DB query filter is tenant-scoped",
)
async def validate_query(
    body: ValidateQueryRequest,
    svc: IsoSvcDep,
) -> ValidateQueryResponse:
    return await svc.validate_query(body.caller_tenant_id, body.query_filter)


@router.get(
    "/policies",
    response_model=PolicyListResponse,
    summary="List isolation policies for a tenant",
)
async def list_policies(
    svc: IsoSvcDep,
    tenant_id: UUID = Query(..., description="Filter by tenant ID."),
    next_cursor: str | None = Query(default=None),
    limit: int = Query(
        default=DEFAULT_PAGINATION_LIMIT, ge=1, le=MAX_PAGINATION_LIMIT
    ),
) -> PolicyListResponse:
    page = await svc.list_policies(tenant_id, next_cursor=next_cursor, limit=limit)
    return PolicyListResponse(
        items=[PolicyResponse.model_validate(p) for p in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.patch(
    "/policies/{policy_id}",
    response_model=PolicyResponse,
    responses=RESPONSES_READ,
    summary="Update an isolation policy",
)
async def update_policy(
    policy: PolicyDep,
    body: PolicyUpdateRequest,
    svc: IsoSvcDep,
) -> PolicyResponse:
    updated = await svc.update_policy(policy.id, body)
    return PolicyResponse.model_validate(updated)


@router.post(
    "/claims",
    response_model=ResourceClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a resource claim",
)
@limiter.limit("60/minute")
async def create_claim(
    request: Request,
    body: ResourceClaimRequest,
    svc: ClaimSvcDep,
) -> ResourceClaimResponse:
    claim = await svc.claim(
        body.tenant_id,
        body.resource_id,
        str(body.resource_type),
        body.source_service,
    )
    return ResourceClaimResponse.model_validate(claim)


@router.delete(
    "/claims",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Release a resource claim",
)
async def release_claim(
    body: ReleaseClaimRequest,
    svc: ClaimSvcDep,
) -> None:
    await svc.release(body.tenant_id, body.resource_id, str(body.resource_type))


@router.get(
    "/decisions",
    response_model=DecisionListResponse,
    summary="List access decision log entries for a tenant",
)
async def list_decisions(
    svc: IsoSvcDep,
    db: DbDep,
    tenant_id: UUID = Query(..., description="Caller tenant ID to filter by."),
    next_cursor: str | None = Query(default=None),
    limit: int = Query(
        default=DEFAULT_PAGINATION_LIMIT, ge=1, le=MAX_PAGINATION_LIMIT
    ),
) -> DecisionListResponse:
    from app.repositories.access_decision_log import AccessDecisionLogRepository
    from app.schemas.isolation import AccessDecisionLogResponse

    repo = AccessDecisionLogRepository(db)
    page = await repo.list_by_tenant(tenant_id, next_cursor=next_cursor, limit=limit)
    return DecisionListResponse(
        items=[AccessDecisionLogResponse.model_validate(d) for d in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )
