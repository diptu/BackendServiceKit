"""Domain events — published to RabbitMQ's identity.events exchange.

IAM's UserProjection (services/IAM/app/models/user_projection.py) is the
intended consumer: id, tenant_id, email, display_name, status, synced_at.
Payloads here carry enough to populate that projection directly. Wiring
IAM's actual consumer remains separate, deferred work (see IAM's own
TODO.md) — this service only needs to publish correctly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserCreated:
    user_id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    status: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class UserUpdated:
    user_id: UUID
    tenant_id: UUID
    changed_fields: list[str]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class UserStatusChanged:
    user_id: UUID
    tenant_id: UUID
    from_status: str
    to_status: str
    reason: str | None = None
    performed_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class UserDeleted:
    user_id: UUID
    tenant_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class UserRestored:
    user_id: UUID
    tenant_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class InvitationCreated:
    invitation_id: UUID
    tenant_id: UUID
    email: str
    invited_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class InvitationAccepted:
    invitation_id: UUID
    tenant_id: UUID
    user_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class InvitationRevoked:
    invitation_id: UUID
    tenant_id: UUID
    revoked_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
