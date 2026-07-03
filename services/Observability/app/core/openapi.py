"""OpenAPI tag metadata."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Health", "description": "This service's own liveness/readiness probes."},
    {
        "name": "Observability",
        "description": (
            "Operator-only, read-only investigation/correlation API. "
            "Composes Logging, DistributedTracing, MetricsCollection, "
            "Monitoring, Alerting, and HealthCheck — never calls a tier-1 "
            "backend directly. `root-cause`/`correlation`/`anomalies` "
            "surface correlated evidence, not an automated diagnosis — "
            "see TODO.md Decisions #7/#8."
        ),
    },
]

RESPONSES_COMMON: dict[int | str, dict[str, Any]] = {
    403: {"description": "Operator (platform-admin) role required."},
}
