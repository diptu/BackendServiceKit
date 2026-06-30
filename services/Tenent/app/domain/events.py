"""Domain events — merged from all three services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# TenantManagement events
# ---------------------------------------------------------------------------


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
    provisioned_by: UUID | None = None
    reason: str | None = None
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


@dataclass
class TenantConfigurationUpdated:
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


# ---------------------------------------------------------------------------
# TenantLifecycle events
# ---------------------------------------------------------------------------


@dataclass
class TenantPended:
    tenant_id: UUID
    pended_by: UUID | None = None
    reason: str | None = None
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
class TenantUnlocked:
    tenant_id: UUID
    unlocked_by: UUID | None = None
    reason: str | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# TenantIsolation events
# ---------------------------------------------------------------------------


@dataclass
class IsolationViolationDetected:
    caller_tenant_id: UUID
    target_tenant_id: UUID | None
    resource_id: str
    resource_type: str
    action: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class ResourceClaimed:
    tenant_id: UUID
    resource_id: str
    resource_type: str
    source_service: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class ResourceClaimReleased:
    tenant_id: UUID
    resource_id: str
    resource_type: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class PolicyUpdated:
    tenant_id: UUID
    policy_id: UUID
    changes: dict[str, object]
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
