"""Pydantic schemas for AbacPolicy CRUD and policy-evaluation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.domain.enums import PolicyEffect
from app.schemas.base import AppBaseModel


class CreatePolicyRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID header."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    effect: PolicyEffect
    resource_type: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=100)
    conditions: dict[str, Any] | None = None
    priority: int = 0
    is_active: bool = True


class UpdatePolicyRequest(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    effect: PolicyEffect | None = None
    resource_type: str | None = Field(None, min_length=1, max_length=100)
    action: str | None = Field(None, min_length=1, max_length=100)
    conditions: dict[str, Any] | None = None
    priority: int | None = None
    is_active: bool | None = None


class PolicyResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    effect: PolicyEffect
    resource_type: str
    action: str
    conditions: dict[str, Any] | None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class PolicyListResponse(AppBaseModel):
    items: list[PolicyResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool


class EvaluateRequest(AppBaseModel):
    user_id: UUID
    resource_type: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=100)
    resource_attributes: dict[str, Any] | None = None


class EvaluateResponse(AppBaseModel):
    allowed: bool
    reason: str
    matched_policy_id: UUID | None = None
