"""Domain events published by the API Gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class GatewayRequestCompleted:
    """Emitted after every proxied request, regardless of outcome."""

    request_id: str
    method: str
    path: str
    upstream: str
    status_code: int
    latency_ms: float
    cache_result: str        # hit | miss | skip | error
    tenant_id: str | None
    occurred_at: datetime = field(default_factory=_now)


@dataclass
class TenantCacheInvalidated:
    """Emitted after all cache entries for a tenant are purged."""

    tenant_id: str
    triggered_by: str        # "write_request" | "rabbitmq_event"
    keys_deleted: int
    occurred_at: datetime = field(default_factory=_now)
