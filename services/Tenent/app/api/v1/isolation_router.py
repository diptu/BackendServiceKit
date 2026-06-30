"""Tenant isolation enforcement and policy management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import DbDep, PolicyDep
from app.domain.exceptions import (
    ContextResolutionError,
    InvalidQueryFilterError,
    IsolationValidationError,
    IsolationViolationError,
    PolicyNotFoundError,
    ResourceClaimConflictError,
    ResourceClaimNotFoundError,
)
from app.schemas.isolation import (
    AccessDecisionLogResponse,
    BulkClaimRequest,
    CheckAccessRequest,
    CheckAccessResponse,
    DecisionListResponse,
    PolicyCreateRequest,
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
from app.validators.isolation_validator import validate_policy_update

router = APIRouter(prefix="/isolation", tags=["Isolation"])


def _svc(db: AsyncSession) -> IsolationService:
    return IsolationService(db)


def _claim_svc(db: AsyncSession) -> ResourceClaimService:
    return ResourceClaimService(db)


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


@router.post("/validate", response_model=ValidateResponse)
async def validate(body: ValidateRequest, db: DbDep) -> ValidateResponse:
    allowed, decision, reason = await _svc(db).validate(
        body.caller_tenant_id,
        body.target_tenant_id,
        resource_id=body.resource_id,
        resource_type=body.resource_type,
    )
    return ValidateResponse(allowed=allowed, decision=decision, reason=reason)


# ---------------------------------------------------------------------------
# Check Access
# ---------------------------------------------------------------------------


@router.post("/check-access", response_model=CheckAccessResponse)
async def check_access(body: CheckAccessRequest, db: DbDep) -> CheckAccessResponse:
    try:
        allowed, decision, reason, cache_hit = await _svc(db).check_access(
            body.caller_tenant_id,
            body.target_tenant_id,
            body.resource_id,
            body.resource_type,
            body.action,
        )
    except IsolationViolationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return CheckAccessResponse(
        allowed=allowed, decision=decision, reason=reason, cache_hit=cache_hit
    )


# ---------------------------------------------------------------------------
# Resolve Context
# ---------------------------------------------------------------------------


@router.post("/resolve-context", response_model=ResolveContextResponse)
async def resolve_context(
    body: ResolveContextRequest, db: DbDep
) -> ResolveContextResponse:
    try:
        ctx = await _svc(db).resolve_context(body.token)
    except ContextResolutionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return ResolveContextResponse(**ctx)


# ---------------------------------------------------------------------------
# Validate Resource
# ---------------------------------------------------------------------------


@router.post("/validate-resource", response_model=ValidateResourceResponse)
async def validate_resource(
    body: ValidateResourceRequest, db: DbDep
) -> ValidateResourceResponse:
    try:
        valid, reason, owner = await _svc(db).validate_resource(
            body.caller_tenant_id,
            body.resource_id,
            body.resource_type,
        )
    except ResourceClaimNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ValidateResourceResponse(valid=valid, reason=reason, owner_tenant_id=owner)


# ---------------------------------------------------------------------------
# Validate Query
# ---------------------------------------------------------------------------


@router.post("/validate-query", response_model=ValidateQueryResponse)
async def validate_query(
    body: ValidateQueryRequest, db: DbDep
) -> ValidateQueryResponse:
    try:
        valid, reason = await _svc(db).validate_query(
            body.caller_tenant_id, body.filters
        )
    except InvalidQueryFilterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ValidateQueryResponse(valid=valid, reason=reason)


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    db: DbDep,
    tenant_id: UUID = Query(...),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> PolicyListResponse:
    page = await _svc(db).list_policies(tenant_id, cursor=cursor, limit=limit)
    return PolicyListResponse(
        items=[PolicyResponse.model_validate(p) for p in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreateRequest,
    db: DbDep,
    tenant_id: UUID = Query(...),
) -> PolicyResponse:
    policy = await _svc(db).create_policy(
        tenant_id=tenant_id,
        name=body.name,
        policy_type=body.policy_type,
        allow_cross_tenant_read=body.allow_cross_tenant_read,
        allowed_partner_tenant_ids=body.allowed_partner_tenant_ids,
    )
    return PolicyResponse.model_validate(policy)


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy: PolicyDep) -> PolicyResponse:
    return PolicyResponse.model_validate(policy)


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy: PolicyDep, body: PolicyUpdateRequest, db: DbDep
) -> PolicyResponse:
    raw = body.model_dump(exclude_none=True)
    try:
        updates = validate_policy_update(raw)
    except IsolationValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        updated = await _svc(db).update_policy(policy.id, updates)
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PolicyResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# Resource Claims
# ---------------------------------------------------------------------------


@router.post("/claims", response_model=ResourceClaimResponse, status_code=201)
async def claim_resource(
    body: ResourceClaimRequest, db: DbDep
) -> ResourceClaimResponse:
    try:
        claim = await _claim_svc(db).claim(
            tenant_id=body.tenant_id,
            resource_id=body.resource_id,
            resource_type=str(body.resource_type),
            source_service=body.source_service,
        )
    except ResourceClaimConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ResourceClaimResponse.model_validate(claim)


@router.post(
    "/claims/bulk", response_model=list[ResourceClaimResponse], status_code=201
)
async def bulk_claim(
    body: BulkClaimRequest, db: DbDep, tenant_id: UUID = Query(...)
) -> list[ResourceClaimResponse]:
    claims_input = [
        {"resource_id": c.resource_id, "resource_type": str(c.resource_type)}
        for c in body.claims
    ]
    try:
        claims = await _claim_svc(db).bulk_claim(
            tenant_id=tenant_id,
            claims=claims_input,
            source_service=body.source_service,
        )
    except ResourceClaimConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return [ResourceClaimResponse.model_validate(c) for c in claims]


@router.get("/claims", response_model=list[ResourceClaimResponse])
async def list_claims(
    db: DbDep,
    tenant_id: UUID = Query(...),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[ResourceClaimResponse]:
    page = await _claim_svc(db).list(tenant_id, cursor=cursor, limit=limit)
    return [ResourceClaimResponse.model_validate(c) for c in page.items]


@router.delete("/claims", status_code=204)
async def release_claim(body: ReleaseClaimRequest, db: DbDep) -> None:
    await _claim_svc(db).release(
        tenant_id=body.tenant_id,
        resource_id=body.resource_id,
        resource_type=str(body.resource_type),
    )


# ---------------------------------------------------------------------------
# Audit Decision Logs
# ---------------------------------------------------------------------------


@router.get("/decisions", response_model=DecisionListResponse)
async def list_decisions(
    db: DbDep,
    tenant_id: UUID = Query(...),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> DecisionListResponse:
    page = await _svc(db).list_decisions(tenant_id, cursor=cursor, limit=limit)
    return DecisionListResponse(
        items=[AccessDecisionLogResponse.model_validate(d) for d in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )
