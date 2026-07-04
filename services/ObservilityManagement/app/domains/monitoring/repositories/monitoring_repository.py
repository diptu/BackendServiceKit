"""Domain model + parsing for the Monitoring domain.

A field being `None` means "the source for this couldn't be reached,"
never "zero" — same convention every aggregator in this service uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ServiceHealth:
    name: str
    base_url: str
    reachable: bool
    status_code: int | None = None
    latency_ms: float | None = None
    detail: str | None = None


@dataclass(frozen=True)
class ResourceHealth:
    postgres_reachable: bool | None
    redis_reachable: bool | None
    rabbitmq_reachable: bool | None


@dataclass(frozen=True)
class TenantSummary:
    total: int
    by_status: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ClusterInfo:
    name: str
    environment: str
    service_count: int


@dataclass(frozen=True)
class PlatformStatus:
    overall_status: str
    services: list[ServiceHealth] = field(default_factory=list)
    active_alert_count: int | None = None


def services_from_gateway_status(gateway_status: dict[str, Any] | None) -> list[ServiceHealth]:
    """Parse APIGateway's /api/v1/gateway/status `upstreams` list.

    Defensive on purpose: a schema change on APIGateway's side degrades to
    an empty list, not a crash of the whole aggregation.
    """
    if not gateway_status:
        return []
    upstreams = gateway_status.get("upstreams")
    if not isinstance(upstreams, list):
        return []
    results = []
    for entry in upstreams:
        if not isinstance(entry, dict):
            continue
        results.append(
            ServiceHealth(
                name=str(entry.get("name", "unknown")),
                base_url=str(entry.get("base_url", "")),
                reachable=bool(entry.get("reachable", False)),
                status_code=entry.get("status_code"),
                latency_ms=entry.get("latency_ms"),
            )
        )
    return results


def extract_dependency(ready_body: dict[str, Any] | None, name: str) -> bool | None:
    """Tenent's `/ready` shape: `dependencies` is a *list* of
    `{"name", "status": "up"|"down", ...}` dicts."""
    if not ready_body or not isinstance(ready_body, dict):
        return None
    deps = ready_body.get("dependencies")
    if not isinstance(deps, list):
        return None
    for dep in deps:
        if isinstance(dep, dict) and dep.get("name") == name:
            status = dep.get("status")
            return status is not None and str(status).lower() == "up"
    return None


def first_non_none(*values: bool | None) -> bool | None:
    for v in values:
        if v is not None:
            return v
    return None


def overall_status(services: list[ServiceHealth]) -> str:
    if not services:
        return "unknown"
    reachable_count = sum(1 for s in services if s.reachable)
    if reachable_count == len(services):
        return "healthy"
    if reachable_count == 0:
        return "unhealthy"
    return "degraded"
