"""Request and response schemas for provisioning endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field

from app.domain.enums import JobStatus
from app.schemas.base import AppBaseModel


class StartProvisioningRequest(AppBaseModel):
    tenant_id: UUID
    metadata: dict[str, str] | None = None


class RetryRequest(AppBaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AddResourceRequest(AppBaseModel):
    resource_type: str = Field(max_length=100)
    resource_id: str = Field(max_length=500)
    status: str = Field(default="provisioned", max_length=50)
    meta: dict[str, Any] | None = None


class JobResponse(AppBaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

    id: UUID
    tenant_id: UUID
    status: JobStatus
    celery_task_id: str | None
    completed_steps: list[str]
    current_step: str | None
    total_steps: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobSummary(AppBaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

    id: UUID
    tenant_id: UUID
    status: JobStatus
    current_step: str | None
    total_steps: int
    created_at: datetime
    updated_at: datetime


class JobListResponse(AppBaseModel):
    items: list[JobSummary]
    total: int
    has_more: bool
    next_cursor: str | None


class ResourceResponse(AppBaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)

    id: UUID
    job_id: UUID | None
    tenant_id: UUID
    resource_type: str
    resource_id: str
    status: str
    meta: dict[str, Any] | None
    provisioned_at: datetime | None
    created_at: datetime


class TenantProvisioningStatusResponse(AppBaseModel):
    tenant_id: UUID
    latest_job: JobResponse | None
    resources: list[ResourceResponse]
