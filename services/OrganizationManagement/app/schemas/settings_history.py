"""Pydantic schemas for the organization settings version-history endpoint."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.base import AppBaseModel


class OrganizationSettingsHistoryResponse(AppBaseModel):
    id: UUID
    organization_id: UUID
    version: int
    snapshot: dict[str, object]
    changed_by: UUID | None
    changed_at: datetime


class OrganizationSettingsHistoryListResponse(AppBaseModel):
    items: list[OrganizationSettingsHistoryResponse]
    total: int
    has_more: bool = False
