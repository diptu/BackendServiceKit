"""Pydantic schemas for the organization audit-trail endpoint."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.base import AppBaseModel


class OrganizationEventResponse(AppBaseModel):
    id: UUID
    organization_id: UUID
    tenant_id: UUID
    event_type: str
    payload: dict[str, object]
    performed_by: UUID | None
    occurred_at: datetime


class OrganizationEventListResponse(AppBaseModel):
    items: list[OrganizationEventResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
