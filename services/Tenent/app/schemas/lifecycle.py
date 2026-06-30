"""Pydantic schemas for TenantLifecycle endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import TenantLifecycleStatus, TransitionType
from app.schemas.base import AppBaseModel


class TransitionRequest(AppBaseModel):
    reason: str | None = Field(None, max_length=500)
    performed_by: UUID | None = None
    source: str = "api"


class LifecycleStateResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    current_status: TenantLifecycleStatus
    previous_status: TenantLifecycleStatus | None = None
    created_at: datetime
    updated_at: datetime


class LifecycleEventResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    from_status: TenantLifecycleStatus | None = None
    to_status: TenantLifecycleStatus
    transition: TransitionType
    reason: str | None = None
    performed_by: UUID | None = None
    source: str
    occurred_at: datetime


class LifecycleHistoryResponse(AppBaseModel):
    tenant_id: UUID
    current_status: TenantLifecycleStatus | None = None
    events: list[LifecycleEventResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool
