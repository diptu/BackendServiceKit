"""Domain events published by the Tenant Management Service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.enums import TenantStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TenantCreated:
    tenant_id: UUID
    name: str
    region: str
    owner_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantUpdated:
    tenant_id: UUID
    updated_by: UUID
    changed_fields: list[str]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantProvisioningStarted:
    tenant_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantProvisioningCompleted:
    tenant_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantProvisioningFailed:
    tenant_id: UUID
    reason: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantActivated:
    tenant_id: UUID
    activated_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantSuspended:
    tenant_id: UUID
    suspended_by: UUID
    reason: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantReactivated:
    tenant_id: UUID
    reactivated_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantArchived:
    tenant_id: UUID
    archived_by: UUID
    previous_status: TenantStatus
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantDeleted:
    tenant_id: UUID
    deleted_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantConfigurationUpdated:
    tenant_id: UUID
    updated_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantBrandingUpdated:
    tenant_id: UUID
    updated_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantOwnerAdded:
    tenant_id: UUID
    user_id: UUID
    role: str
    added_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class TenantOwnerRemoved:
    tenant_id: UUID
    user_id: UUID
    removed_by: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
