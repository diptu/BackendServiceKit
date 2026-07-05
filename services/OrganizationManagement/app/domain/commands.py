"""Domain command objects."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateOrganizationCmd:
    tenant_id: UUID
    name: str
    slug: str
    description: str | None = None


@dataclass
class UpdateOrganizationCmd:
    name: str | None = None
    description: str | None = None


@dataclass
class UpdateOrganizationSettingsCmd:
    timezone: str | None = None
    locale: str | None = None
    default_member_role: str | None = None
    feature_flags: dict[str, bool] | None = None
    compliance_rules: dict[str, str] | None = None
