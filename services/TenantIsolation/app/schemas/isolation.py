"""Request and response schemas for isolation endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.domain.enums import AccessAction, IsolationDecision, PolicyType, ResourceType
from app.schemas.base import AppBaseModel


class ValidateRequest(AppBaseModel):
    caller_tenant_id: UUID
    resource_ids: list[str] = Field(..., min_length=1, max_length=100)
    resource_type: ResourceType


class ValidateResponse(AppBaseModel):
    decision: IsolationDecision
    violations: list[str]
    caller_tenant_id: UUID
    resource_type: str


class CheckAccessRequest(AppBaseModel):
    caller_tenant_id: UUID
    target_tenant_id: UUID
    resource_id: str = Field(..., max_length=500)
    resource_type: ResourceType
    action: AccessAction


class CheckAccessResponse(AppBaseModel):
    decision: IsolationDecision
    reason: str | None
    caller_tenant_id: UUID
    target_tenant_id: UUID
    resource_id: str
    resource_type: str
    action: str


class ResolveContextRequest(AppBaseModel):
    token: str


class ResolveContextResponse(AppBaseModel):
    tenant_id: UUID
    user_id: UUID | None
    token_type: str


class ValidateResourceRequest(AppBaseModel):
    caller_tenant_id: UUID
    resource_id: str = Field(..., max_length=500)
    resource_type: ResourceType


class ValidateResourceResponse(AppBaseModel):
    decision: IsolationDecision
    owner_tenant_id: UUID | None


class ValidateQueryRequest(AppBaseModel):
    caller_tenant_id: UUID
    query_filter: dict[str, str]


class ValidateQueryResponse(AppBaseModel):
    is_valid: bool
    reason: str | None


class PolicyResponse(AppBaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

    id: UUID
    tenant_id: UUID
    name: str
    policy_type: PolicyType
    allow_cross_tenant_read: bool
    allowed_partner_tenant_ids: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PolicyListResponse(AppBaseModel):
    items: list[PolicyResponse]
    total: int
    next_cursor: str | None
    has_more: bool


class PolicyUpdateRequest(AppBaseModel):
    name: str | None = None
    policy_type: PolicyType | None = None
    allow_cross_tenant_read: bool | None = None
    allowed_partner_tenant_ids: list[str] | None = None
    is_active: bool | None = None


class ResourceClaimRequest(AppBaseModel):
    tenant_id: UUID
    resource_id: str = Field(..., max_length=500)
    resource_type: ResourceType
    source_service: str = Field(..., max_length=200)


class ClaimItem(AppBaseModel):
    resource_id: str = Field(..., max_length=500)
    resource_type: ResourceType


class BulkClaimRequest(AppBaseModel):
    tenant_id: UUID
    claims: list[ClaimItem] = Field(..., min_length=1, max_length=500)
    source_service: str = Field(..., max_length=200)


class ResourceClaimResponse(AppBaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

    id: UUID
    tenant_id: UUID
    resource_id: str
    resource_type: str
    source_service: str
    claimed_at: datetime


class ReleaseClaimRequest(AppBaseModel):
    tenant_id: UUID
    resource_id: str = Field(..., max_length=500)
    resource_type: ResourceType


class AccessDecisionLogResponse(AppBaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

    id: UUID
    caller_tenant_id: UUID
    target_tenant_id: UUID | None
    resource_id: str
    resource_type: str
    action: str
    decision: str
    reason: str | None
    request_id: str | None
    decided_at: datetime


class DecisionListResponse(AppBaseModel):
    items: list[AccessDecisionLogResponse]
    total: int
    next_cursor: str | None
    has_more: bool
