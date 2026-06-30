"""Domain events emitted by the isolation service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
