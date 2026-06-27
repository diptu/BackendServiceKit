"""Domain events published by the Tenant Lifecycle Service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TenantActivated:
    tenant_id: UUID
    activated_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantSuspended:
    tenant_id: UUID
    suspended_by: UUID | None = None
    reason: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantReactivated:
    tenant_id: UUID
    reactivated_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantLocked:
    tenant_id: UUID
    locked_by: UUID | None = None
    reason: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantArchived:
    tenant_id: UUID
    archived_by: UUID | None = None
    previous_status: str = "active"
    reason: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantDeleted:
    tenant_id: UUID
    deleted_by: UUID | None = None
    reason: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
