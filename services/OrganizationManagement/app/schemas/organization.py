"""Pydantic schemas for Organization endpoints."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.domain.enums import OrganizationStatus
from app.schemas.base import AppBaseModel

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


class CreateOrganizationRequest(AppBaseModel):
    """tenant_id is not a field here — it comes from the required
    X-Tenant-ID header (see api/v1/dependencies.py), the same routing
    identifier every other endpoint on this router is scoped by."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)

    @field_validator("slug")
    @classmethod
    def _validate_slug(cls, value: str) -> str:
        if not _SLUG_PATTERN.match(value):
            raise ValueError(
                "slug must be lowercase alphanumeric with single hyphens, e.g. 'acme-corp'."
            )
        return value


class UpdateOrganizationRequest(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class OrganizationResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class OrganizationListResponse(AppBaseModel):
    items: list[OrganizationResponse]
    total: int
    next_cursor: str | None = None
    has_more: bool


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class UpdateOrganizationSettingsRequest(AppBaseModel):
    timezone: str | None = None
    locale: str | None = None
    default_member_role: str | None = None
    feature_flags: dict[str, bool] | None = None
    compliance_rules: dict[str, str] | None = None


class OrganizationSettingsResponse(AppBaseModel):
    id: UUID
    organization_id: UUID
    timezone: str
    locale: str
    default_member_role: str
    feature_flags: dict[str, bool]
    compliance_rules: dict[str, str]
    updated_at: datetime


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class OrganizationStatsResponse(AppBaseModel):
    organization_id: UUID
    status: OrganizationStatus
    created_at: datetime
    member_count: int
    workspace_count: int
    team_count: int
    group_count: int


# ---------------------------------------------------------------------------
# Sub-resource enumeration (Members / Workspaces / Teams / Groups)
# ---------------------------------------------------------------------------


class SubResourceListResponse(AppBaseModel):
    items: list[object]
    total: int
