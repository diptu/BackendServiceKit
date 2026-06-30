"""Domain command objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class CreateTenantCmd:
    name: str
    display_name: str
    owner_id: UUID
    region: str
    description: str | None = None
    timezone: str = "UTC"
    locale: str = "en-US"
    currency: str = "USD"


@dataclass
class UpdateTenantCmd:
    display_name: str | None = None
    description: str | None = None
    region: str | None = None
    timezone: str | None = None
    locale: str | None = None
    currency: str | None = None


@dataclass
class UpdateTenantSettingsCmd:
    timezone: str | None = None
    locale: str | None = None
    language: str | None = None
    date_format: str | None = None
    number_format: str | None = None
    currency: str | None = None
    session_timeout_minutes: int | None = None
    default_theme: str | None = None


@dataclass
class AddOwnerCmd:
    user_id: UUID
    role: str = "owner"


@dataclass
class UpdateTenantMetadataCmd:
    metadata: dict[str, str] = field(default_factory=dict)
