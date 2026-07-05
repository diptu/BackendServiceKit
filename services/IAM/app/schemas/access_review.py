"""Pydantic schemas for Access Review endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import AccessReviewStatus
from app.schemas.base import AppBaseModel


class CreateAccessReviewRequest(AppBaseModel):
    """tenant_id is not a field — it comes from the required X-Tenant-ID header."""

    subject_user_id: UUID
    resource_type: str = Field(..., min_length=1, max_length=100)
    resource_id: UUID
    reviewer_id: UUID | None = None


class RecordAccessReviewDecisionRequest(AppBaseModel):
    status: AccessReviewStatus
    decision_notes: str | None = Field(None, max_length=2000)
    reviewer_id: UUID | None = None


class AccessReviewResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    subject_user_id: UUID
    reviewer_id: UUID | None
    resource_type: str
    resource_id: UUID
    status: AccessReviewStatus
    decision_notes: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None


class AccessReviewListResponse(AppBaseModel):
    items: list[AccessReviewResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool
