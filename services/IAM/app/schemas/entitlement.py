"""Pydantic schemas for Entitlement endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import EntitlementStatus
from app.schemas.base import AppBaseModel

_EntitlementValue = str | float | bool | list[object]


class CreateEntitlementRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID header."""

    user_id: UUID
    key: str = Field(..., min_length=1, max_length=255)
    value: _EntitlementValue | None = None
    performed_by: UUID | None = None


class EntitlementResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    key: str
    value: _EntitlementValue | None
    status: EntitlementStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class EntitlementListResponse(AppBaseModel):
    items: list[EntitlementResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool
