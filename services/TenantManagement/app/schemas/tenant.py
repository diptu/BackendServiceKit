"""Pydantic request/response schemas for tenant resources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.core.constants import (
    DEFAULT_CURRENCY,
    DEFAULT_DATE_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_LOCALE,
    DEFAULT_SESSION_TIMEOUT_MINUTES,
    DEFAULT_THEME,
    DEFAULT_TIMEZONE,
    TENANT_DESCRIPTION_MAX_LENGTH,
    TENANT_NAME_MAX_LENGTH,
    TENANT_SLUG_PATTERN,
)
from app.domain.enums import OwnerRole, TenantStatus
from app.schemas.base import AppBaseModel

# Shared example values used across multiple schemas
_EX_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"
_EX_USER_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
_EX_SETTINGS_ID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------


class CreateTenantRequest(AppBaseModel):
    """Request body for creating a new tenant."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=TENANT_NAME_MAX_LENGTH,
        pattern=TENANT_SLUG_PATTERN,
        description="Globally unique URL-safe slug. Immutable after creation.",
        examples=["alphabet-corp"],
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=TENANT_NAME_MAX_LENGTH,
        description="Human-readable tenant name shown in the UI.",
        examples=["Alphabet Corporation"],
    )
    description: str | None = Field(
        default=None,
        max_length=TENANT_DESCRIPTION_MAX_LENGTH,
        description="Optional free-text description of the tenant.",
        examples=["Enterprise SaaS customer — Google parent company."],
    )
    owner_id: UUID = Field(
        ...,
        description="UUID of the user who becomes the initial owner.",
        examples=[_EX_USER_ID],
    )
    region: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Deployment region for data-residency purposes (e.g. `us-east-1`).",
        examples=["us-east-1"],
    )
    timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        max_length=100,
        description="IANA timezone string.",
        examples=["America/New_York"],
    )
    locale: str = Field(
        default=DEFAULT_LOCALE,
        max_length=20,
        description="BCP-47 locale string.",
        examples=["en-US"],
    )
    currency: str = Field(
        default=DEFAULT_CURRENCY,
        max_length=10,
        description="ISO 4217 currency code.",
        examples=["USD"],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "name": "alphabet-corp",
                "display_name": "Alphabet Corporation",
                "description": "Enterprise SaaS customer — Google parent company.",
                "owner_id": _EX_USER_ID,
                "region": "us-east-1",
                "timezone": "America/New_York",
                "locale": "en-US",
                "currency": "USD",
            }
        },
    )


class UpdateTenantRequest(AppBaseModel):
    """Request body for partially updating a tenant. All fields are optional."""

    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=TENANT_NAME_MAX_LENGTH,
        description="New human-readable name.",
        examples=["Alphabet Corp (Updated)"],
    )
    description: str | None = Field(
        default=None,
        max_length=TENANT_DESCRIPTION_MAX_LENGTH,
        description="Updated description.",
        examples=["Updated description."],
    )
    region: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="New deployment region.",
        examples=["eu-west-1"],
    )
    timezone: str | None = Field(
        default=None,
        max_length=100,
        description="New IANA timezone string.",
        examples=["Europe/London"],
    )
    locale: str | None = Field(
        default=None,
        max_length=20,
        description="New BCP-47 locale.",
        examples=["en-GB"],
    )
    currency: str | None = Field(
        default=None,
        max_length=10,
        description="New ISO 4217 currency code.",
        examples=["GBP"],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "display_name": "Alphabet Corp (Updated)",
                "timezone": "Europe/London",
                "locale": "en-GB",
                "currency": "GBP",
            }
        },
    )


class TenantResponse(AppBaseModel):
    """Full tenant representation returned on create / get / update."""

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
    deleted_at: datetime | None

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EX_TENANT_ID,
                "name": "alphabet-corp",
                "display_name": "Alphabet Corporation",
                "description": "Enterprise SaaS customer.",
                "status": "active",
                "region": "us-east-1",
                "timezone": "America/New_York",
                "locale": "en-US",
                "currency": "USD",
                "owner_id": _EX_USER_ID,
                "created_at": "2026-01-15T09:00:00Z",
                "updated_at": "2026-06-01T12:30:00Z",
                "deleted_at": None,
            }
        },
    )


class TenantSummary(AppBaseModel):
    """Lightweight tenant representation used in list responses."""

    id: UUID
    name: str
    display_name: str
    status: TenantStatus
    region: str
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EX_TENANT_ID,
                "name": "alphabet-corp",
                "display_name": "Alphabet Corporation",
                "status": "active",
                "region": "us-east-1",
                "created_at": "2026-01-15T09:00:00Z",
            }
        },
    )


class TenantListResponse(AppBaseModel):
    """Paginated list of tenants."""

    items: list[TenantSummary]
    total: int = Field(
        ..., description="Total number of tenants matching the filter.", examples=[42]
    )
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for the next page. `null` when no more pages.",
        examples=["eyJpZCI6IjU1MGU4NDAwIn0="],
    )
    has_more: bool = Field(..., description="Whether additional pages are available.")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": _EX_TENANT_ID,
                        "name": "alphabet-corp",
                        "display_name": "Alphabet Corporation",
                        "status": "active",
                        "region": "us-east-1",
                        "created_at": "2026-01-15T09:00:00Z",
                    }
                ],
                "total": 1,
                "next_cursor": None,
                "has_more": False,
            }
        },
    )


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


class TransitionRequest(AppBaseModel):
    """Optional body for lifecycle transition endpoints."""

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Human-readable reason for the transition. Required for `suspend`.",
        examples=["Non-payment — subscription expired 2026-06-01."],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {"reason": "Non-payment — subscription expired 2026-06-01."}
        },
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class UpdateTenantSettingsRequest(AppBaseModel):
    """Partial update of tenant configuration. All fields are optional."""

    timezone: str | None = Field(
        default=None,
        max_length=100,
        description="IANA timezone string.",
        examples=["America/Chicago"],
    )
    locale: str | None = Field(
        default=None,
        max_length=20,
        description="BCP-47 locale.",
        examples=["en-US"],
    )
    language: str | None = Field(
        default=None,
        max_length=20,
        description="ISO 639-1 language code.",
        examples=["en"],
    )
    date_format: str | None = Field(
        default=None,
        max_length=50,
        description="Date display format token.",
        examples=["MM/DD/YYYY"],
    )
    number_format: str | None = Field(
        default=None,
        max_length=50,
        description="Number display format token.",
        examples=["#,###.##"],
    )
    currency: str | None = Field(
        default=None,
        max_length=10,
        description="ISO 4217 currency code.",
        examples=["USD"],
    )
    session_timeout_minutes: int | None = Field(
        default=None,
        ge=5,
        le=1440,
        description="Idle session timeout in minutes (5–1440).",
        examples=[60],
    )
    default_theme: str | None = Field(
        default=None,
        max_length=50,
        description="UI theme identifier.",
        examples=["light"],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "timezone": "America/Chicago",
                "locale": "en-US",
                "session_timeout_minutes": 30,
                "default_theme": "dark",
            }
        },
    )


class TenantSettingsResponse(AppBaseModel):
    """Full tenant settings record."""

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

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EX_SETTINGS_ID,
                "tenant_id": _EX_TENANT_ID,
                "timezone": "America/New_York",
                "locale": "en-US",
                "language": "en",
                "date_format": "YYYY-MM-DD",
                "number_format": "#,###.##",
                "currency": "USD",
                "session_timeout_minutes": 60,
                "default_theme": "light",
                "updated_at": "2026-06-01T12:30:00Z",
            }
        },
    )


class TenantSettingsDefaults(AppBaseModel):
    timezone: str = DEFAULT_TIMEZONE
    locale: str = DEFAULT_LOCALE
    language: str = DEFAULT_LANGUAGE
    date_format: str = DEFAULT_DATE_FORMAT
    number_format: str = "#,###.##"
    currency: str = DEFAULT_CURRENCY
    session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES
    default_theme: str = DEFAULT_THEME


# ---------------------------------------------------------------------------
# Owners / Contacts
# ---------------------------------------------------------------------------


class AddOwnerRequest(AppBaseModel):
    """Request body to add an owner or admin to a tenant."""

    user_id: UUID = Field(
        ...,
        description="UUID of the user to add.",
        examples=[_EX_USER_ID],
    )
    role: OwnerRole = Field(
        default=OwnerRole.OWNER,
        description="Role to assign: `owner` or `admin`.",
        examples=["owner"],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={"example": {"user_id": _EX_USER_ID, "role": "owner"}},
    )


class TenantOwnerResponse(AppBaseModel):
    """Single tenant owner record."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    role: str
    added_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                "tenant_id": _EX_TENANT_ID,
                "user_id": _EX_USER_ID,
                "role": "owner",
                "added_at": "2026-01-15T09:00:00Z",
            }
        },
    )


class TenantOwnerListResponse(AppBaseModel):
    """List of tenant owner records."""

    items: list[TenantOwnerResponse]
    total: int = Field(..., description="Total number of active owners.", examples=[1])

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
                        "tenant_id": _EX_TENANT_ID,
                        "user_id": _EX_USER_ID,
                        "role": "owner",
                        "added_at": "2026-01-15T09:00:00Z",
                    }
                ],
                "total": 1,
            }
        },
    )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TenantMetadataEntry(AppBaseModel):
    """A single key-value metadata entry."""

    key: str = Field(..., examples=["industry"])
    value: str = Field(..., examples=["FinTech"])

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
    )


class TenantMetadataResponse(AppBaseModel):
    """All metadata entries for a tenant."""

    tenant_id: UUID
    entries: list[TenantMetadataEntry]

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "tenant_id": _EX_TENANT_ID,
                "entries": [
                    {"key": "industry", "value": "Technology"},
                    {"key": "company_size", "value": "enterprise"},
                    {"key": "customer_tier", "value": "gold"},
                ],
            }
        },
    )


class UpdateTenantMetadataRequest(AppBaseModel):
    """
    Upsert metadata key-value pairs.

    Existing keys are overwritten. New keys are added. No keys are deleted.
    To delete a key, set its value to an empty string.
    """

    metadata: dict[str, str] = Field(
        ...,
        description="Key-value pairs to set or update.",
        examples=[{"industry": "Technology", "customer_tier": "gold"}],
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "metadata": {
                    "industry": "Technology",
                    "company_size": "enterprise",
                    "customer_tier": "gold",
                    "support_plan": "premium",
                }
            }
        },
    )
