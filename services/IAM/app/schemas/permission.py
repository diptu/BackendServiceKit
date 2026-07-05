"""Pydantic schemas for Permission endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import EntityStatus
from app.schemas.base import AppBaseModel


class CreatePermissionRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID header."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="e.g. 'users:read'."
    )
    description: str | None = Field(None, max_length=1000)


class UpdatePermissionRequest(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


class PermissionResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    status: EntityStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class PermissionListResponse(AppBaseModel):
    items: list[PermissionResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool
