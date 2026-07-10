"""AbacPolicy CRUD + the /authorization/evaluate decision endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import (
    PolicyDep,
    PolicyEvaluationServiceDep,
    PolicyServiceDep,
    TenantIdDep,
)
from app.domain.commands import CreatePolicyCmd, UpdatePolicyCmd
from app.domain.exceptions import InvalidPolicyConditionError, PolicyNameConflictError
from app.schemas.policy import (
    CreatePolicyRequest,
    EvaluateRequest,
    EvaluateResponse,
    PolicyListResponse,
    PolicyResponse,
    UpdatePolicyRequest,
)

router = APIRouter(tags=["Policies"])


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: CreatePolicyRequest, tenant_id: TenantIdDep, svc: PolicyServiceDep
) -> PolicyResponse:
    cmd = CreatePolicyCmd(
        tenant_id=tenant_id,
        name=body.name,
        effect=body.effect,
        resource_type=body.resource_type,
        action=body.action,
        description=body.description,
        conditions=body.conditions,
        priority=body.priority,
        is_active=body.is_active,
    )
    try:
        policy = await svc.create(cmd)
    except PolicyNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PolicyResponse.model_validate(policy)


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    tenant_id: TenantIdDep,
    svc: PolicyServiceDep,
    search: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> PolicyListResponse:
    page = await svc.list(
        tenant_id=tenant_id, search=search, cursor=cursor, limit=limit
    )
    return PolicyListResponse(
        items=[PolicyResponse.model_validate(p) for p in page.items],
        total=page.total,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
    )


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy: PolicyDep) -> PolicyResponse:
    return PolicyResponse.model_validate(policy)


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy: PolicyDep,
    body: UpdatePolicyRequest,
    tenant_id: TenantIdDep,
    svc: PolicyServiceDep,
) -> PolicyResponse:
    cmd = UpdatePolicyCmd(
        name=body.name,
        description=body.description,
        effect=body.effect,
        resource_type=body.resource_type,
        action=body.action,
        conditions=body.conditions,
        priority=body.priority,
        is_active=body.is_active,
    )
    try:
        updated = await svc.update(policy.id, tenant_id, cmd)
    except PolicyNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PolicyResponse.model_validate(updated)


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy(
    policy: PolicyDep, tenant_id: TenantIdDep, svc: PolicyServiceDep
) -> None:
    await svc.delete(policy.id, tenant_id)


@router.post("/authorization/evaluate", response_model=EvaluateResponse)
async def evaluate_authorization(
    body: EvaluateRequest, tenant_id: TenantIdDep, svc: PolicyEvaluationServiceDep
) -> EvaluateResponse:
    try:
        decision = await svc.evaluate(
            tenant_id,
            body.user_id,
            body.resource_type,
            body.action,
            resource_attributes=body.resource_attributes,
        )
    except InvalidPolicyConditionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return EvaluateResponse(
        allowed=decision.allowed,
        reason=decision.reason,
        matched_policy_id=decision.matched_policy_id,
    )
