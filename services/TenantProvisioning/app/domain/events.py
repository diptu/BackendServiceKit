"""Domain events emitted during provisioning lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProvisioningStarted:
    tenant_id: UUID
    job_id: UUID
    triggered_by: str = "api"
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class ProvisioningStepCompleted:
    tenant_id: UUID
    job_id: UUID
    step_name: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class ProvisioningCompleted:
    tenant_id: UUID
    job_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class ProvisioningFailed:
    tenant_id: UUID
    job_id: UUID
    failed_step: str
    error_message: str
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
