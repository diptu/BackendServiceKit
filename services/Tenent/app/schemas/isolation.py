"""Pydantic schemas for TenantIsolation endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import (
    AccessAction,
    IsolationDecision,
    PolicyType,
    ResourceType,
)
from app.schemas.base import AppBaseModel


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


class ValidateRequest(AppBaseModel):
    caller_tenant_id: UUID
    target_tenant_id: UUID
    resource_id: str | None = None
    resource_type: str | None = None


class ValidateResponse(AppBaseModel):
    allowed: bool
    decision: IsolationDecision
    reason: str | None = None
    policy_type: PolicyType | None = None


# ---------------------------------------------------------------------------
# Check Access
# ---------------------------------------------------------------------------


class CheckAccessRequest(AppBaseModel):
    caller_tenant_id: UUID
    target_tenant_id: UUID
    resource_id: str
    resource_type: ResourceType
    action: AccessAction


class CheckAccessResponse(AppBaseModel):
    allowed: bool
    decision: IsolationDecision
    reason: str | None = None
    cache_hit: bool = False


# ---------------------------------------------------------------------------
# Resolve Context
# ---------------------------------------------------------------------------


class ResolveContextRequest(AppBaseModel):
    token: str


class ResolveContextResponse(AppBaseModel):
    tenant_id: UUID
    user_id: UUID | None = None
    scopes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Validate Resource / Query
# ---------------------------------------------------------------------------


class ValidateResourceRequest(AppBaseModel):
    caller_tenant_id: UUID
    resource_id: str
    resource_type: ResourceType


class ValidateResourceResponse(AppBaseModel):
    valid: bool
    reason: str | None = None
    owner_tenant_id: UUID | None = None


class ValidateQueryRequest(AppBaseModel):
    caller_tenant_id: UUID
    filters: dict[str, object]


class ValidateQueryResponse(AppBaseModel):
    valid: bool
    reason: str | None = None


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


class PolicyResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    policy_type: PolicyType
    allow_cross_tenant_read: bool
    allowed_partner_tenant_ids: list[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PolicyListResponse(AppBaseModel):
    items: list[PolicyResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool


class PolicyUpdateRequest(AppBaseModel):
    name: str | None = None
    policy_type: PolicyType | None = None
    allow_cross_tenant_read: bool | None = None
    allowed_partner_tenant_ids: list[UUID] | None = None
    is_active: bool | None = None


class PolicyCreateRequest(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    policy_type: PolicyType = PolicyType.STRICT
    allow_cross_tenant_read: bool = False
    allowed_partner_tenant_ids: list[UUID] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Resource Claims
# ---------------------------------------------------------------------------


class ClaimItem(AppBaseModel):
    resource_id: str
    resource_type: ResourceType


class BulkClaimRequest(AppBaseModel):
    claims: list[ClaimItem]
    source_service: str


class ResourceClaimRequest(AppBaseModel):
    tenant_id: UUID
    resource_id: str
    resource_type: ResourceType
    source_service: str


class ResourceClaimResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    resource_id: str
    resource_type: str
    source_service: str
    claimed_at: datetime


class ReleaseClaimRequest(AppBaseModel):
    tenant_id: UUID
    resource_id: str
    resource_type: ResourceType


# ---------------------------------------------------------------------------
# Access Decision Logs
# ---------------------------------------------------------------------------


class AccessDecisionLogResponse(AppBaseModel):
    id: UUID
    caller_tenant_id: UUID
    target_tenant_id: UUID | None = None
    resource_id: str
    resource_type: str
    action: str
    decision: str
    reason: str | None = None
    request_id: str | None = None
    decided_at: datetime


class DecisionListResponse(AppBaseModel):
    items: list[AccessDecisionLogResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool
