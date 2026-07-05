"""Domain command objects.

Simple status-transition operations (activate/suspend/deactivate) take
plain arguments in the service layer instead of a command dataclass — a
wrapper around a status string and an optional reason adds no clarity.
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
