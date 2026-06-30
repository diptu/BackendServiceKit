"""Pydantic schemas for Tenant endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.domain.enums import OwnerRole, TenantStatus
from app.schemas.base import AppBaseModel


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


class CreateTenantRequest(AppBaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    region: str = Field(..., min_length=2)
    timezone: str = "UTC"
    locale: str = "en-US"
    currency: str = "USD"
    owner_id: UUID


class UpdateTenantRequest(AppBaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    timezone: str | None = None
    locale: str | None = None
    currency: str | None = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class TenantResponse(AppBaseModel):
    id: UUID
    name: str
    display_name: str
    description: str | None
    status: TenantStatus
    region: str
    timezone: str
    locale: str
    currency: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class TenantSummary(AppBaseModel):
    id: UUID
    name: str
    display_name: str
    status: TenantStatus
    region: str
    created_at: datetime


class TenantListResponse(AppBaseModel):
    items: list[TenantSummary]
    total: int
    next_cursor: str | None = None
    has_more: bool


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class UpdateTenantSettingsRequest(AppBaseModel):
    timezone: str | None = None
    locale: str | None = None
    language: str | None = None
    date_format: str | None = None
    number_format: str | None = None
    currency: str | None = None
    session_timeout_minutes: int | None = Field(None, ge=5, le=1440)
    default_theme: str | None = None


class TenantSettingsResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    timezone: str
    locale: str
    language: str
    date_format: str
    number_format: str
    currency: str
    session_timeout_minutes: int
    default_theme: str
    updated_at: datetime


# ---------------------------------------------------------------------------
# Owner / Contacts
# ---------------------------------------------------------------------------


class AddOwnerRequest(AppBaseModel):
    user_id: UUID
    role: OwnerRole = OwnerRole.OWNER


class TenantOwnerResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    role: str
    added_at: datetime
    removed_at: datetime | None = None


class TenantOwnerListResponse(AppBaseModel):
    items: list[TenantOwnerResponse]
    total: int


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TenantMetadataEntry(AppBaseModel):
    key: str
    value: str


class TenantMetadataResponse(AppBaseModel):
    tenant_id: UUID
    entries: list[TenantMetadataEntry]
    total: int


class UpdateTenantMetadataRequest(AppBaseModel):
    metadata: dict[str, str]
