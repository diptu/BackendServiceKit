"""Domain events — recorded to OrganizationEvent (the audit trail) on every
mutation. Not published to RabbitMQ: no consumer (Audit Logging /
Notification service) exists yet anywhere in this repo, so publishing would
be speculative infrastructure. Revisit once a real consumer exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OrganizationCreated:
    organization_id: UUID
    tenant_id: UUID
    name: str
    slug: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class OrganizationUpdated:
    organization_id: UUID
    changed_fields: list[str]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class OrganizationDeleted:
    organization_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class OrganizationSettingsUpdated:
    organization_id: UUID
    changed_fields: list[str]
    version: int
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class MemberAdded:
    organization_id: UUID
    user_id: UUID
    role: str
    added_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class MemberRoleChanged:
    organization_id: UUID
    user_id: UUID
    new_role: str
    changed_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class MemberRemoved:
    organization_id: UUID
    user_id: UUID
    removed_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TeamCreated:
    organization_id: UUID
    team_id: UUID
    name: str
    team_type: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TeamUpdated:
    team_id: UUID
    changed_fields: list[str]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TeamDeleted:
    team_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TeamMemberAdded:
    team_id: UUID
    user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TeamMemberRemoved:
    team_id: UUID
    user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class InvitationCreated:
    organization_id: UUID
    invitation_id: UUID
    email: str
    role: str
    invited_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class InvitationAccepted:
    invitation_id: UUID
    organization_id: UUID
    user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class InvitationRevoked:
    invitation_id: UUID
    organization_id: UUID
    revoked_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
