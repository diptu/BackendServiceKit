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


@dataclass
class AddMemberCmd:
    user_id: UUID
    role: str = "member"
    added_by: UUID | None = None


@dataclass
class CreateTeamCmd:
    name: str
    team_type: str = "team"
    description: str | None = None
    parent_team_id: UUID | None = None


@dataclass
class UpdateTeamCmd:
    name: str | None = None
    description: str | None = None


@dataclass
class CreateInvitationCmd:
    email: str
    invited_by: UUID
    role: str = "member"
    expires_in_days: int = 7


@dataclass
class AcceptInvitationCmd:
    token: str
    user_id: UUID
