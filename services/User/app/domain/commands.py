"""Domain command objects.

Status-transition operations (activate/suspend/deactivate/lock/unlock/
onboard/offboard/unsuspend/restore) take plain arguments in the service
layer instead of command dataclasses — a wrapper around a status string
and an optional reason/actor adds no clarity.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateUserCmd:
    tenant_id: UUID
    email: str
    first_name: str
    last_name: str


@dataclass
class UpdateUserCmd:
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@dataclass
class CreateInvitationCmd:
    email: str
    invited_by: UUID
    expires_in_days: int = 7


@dataclass
class AcceptInvitationCmd:
    token: str
    first_name: str
    last_name: str


@dataclass
class UpdateProfileCmd:
    bio: str | None = None
    pronouns: str | None = None
    display_name_override: str | None = None


@dataclass
class UpdatePreferencesCmd:
    locale: str | None = None
    timezone: str | None = None
    extra: dict[str, object] | None = None


@dataclass
class UpdateContactCmd:
    phone: str | None = None
    secondary_email: str | None = None
    address: dict[str, object] | None = None


@dataclass
class SetAvatarCmd:
    url: str
    content_type: str | None = None
