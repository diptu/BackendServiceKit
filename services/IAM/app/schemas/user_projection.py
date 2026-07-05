"""Pydantic schemas for the read-only Users endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.base import AppBaseModel


class UserProjectionResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    status: str
    synced_at: datetime


class UserProjectionListResponse(AppBaseModel):
    items: list[UserProjectionResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool
