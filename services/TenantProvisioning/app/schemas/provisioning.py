"""Pydantic schemas for provisioning endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class ProvisionRequest(AppBaseModel):
    tenant_id: UUID
    subdomain: str = Field(..., min_length=1, max_length=63)
    region: str | None = Field(default=None, max_length=100)


class ProvisioningJobResponse(AppBaseModel):
    tenant_id: UUID
    subdomain: str
    region: str | None = None
    status: str
    current_step: str | None = None
    db_name: str | None = None
    error: str | None = None
    attempts: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ProvisioningJobListResponse(AppBaseModel):
    items: list[ProvisioningJobResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool = False
