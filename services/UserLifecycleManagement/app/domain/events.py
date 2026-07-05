"""Domain events — recorded locally to lifecycle_events, not published.

No RabbitMQ publish this pass: no consumer exists for lifecycle-specific
events yet. See TODO.md's reasoning (matches OrganizationManagement's own
deferral of event publishing for the same reason).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class LifecycleTransitioned:
    user_id: UUID
    tenant_id: UUID
    event_type: str
    from_status: str | None
    to_status: str
    reason: str | None = None
    performed_by: UUID | None = None
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
