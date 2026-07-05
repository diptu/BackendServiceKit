"""Pydantic schemas for lifecycle transition endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import LifecycleStatus
from app.schemas.base import AppBaseModel


class TransitionRequest(AppBaseModel):
    reason: str | None = Field(None, max_length=500)
    performed_by: UUID | None = None


class LockRequest(AppBaseModel):
    reason: str | None = Field(None, max_length=500)
    locked_by: UUID | None = None


class LifecycleStateResponse(AppBaseModel):
    user_id: UUID
    tenant_id: UUID
    status: LifecycleStatus
    locked_reason: str | None
    locked_by: UUID | None
    created_at: datetime
    updated_at: datetime


class RemoteUserResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    status: str
    deleted_at: datetime | None


class LifecycleStatusResponse(AppBaseModel):
    user_id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    remote_status: str
    lifecycle_status: LifecycleStatus
    deleted_at: datetime | None
    locked_reason: str | None
    locked_by: UUID | None
    last_event_type: str | None = None
    last_event_at: datetime | None = None


class LifecycleEventResponse(AppBaseModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    event_type: str
    from_status: str | None
    to_status: str
    reason: str | None
    performed_by: UUID | None
    occurred_at: datetime


class LifecycleEventListResponse(AppBaseModel):
    items: list[LifecycleEventResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
