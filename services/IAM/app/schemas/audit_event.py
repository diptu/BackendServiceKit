"""Pydantic schemas for the Audit Events endpoint."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.base import AppBaseModel


class AuditEventResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    event_type: str
    subject_user_id: UUID | None
    resource_type: str
    resource_id: UUID | None
    actor_id: UUID | None
    details: dict[str, object] | None
    occurred_at: datetime


class AuditEventListResponse(AppBaseModel):
    items: list[AuditEventResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
