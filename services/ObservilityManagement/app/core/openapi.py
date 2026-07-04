"""OpenAPI tag metadata for every merged domain."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Health", "description": "This service's own liveness/readiness probes."},
    {"name": "Logs", "description": "LogQL-backed query layer over Loki."},
    {"name": "Traces", "description": "TraceQL-backed query layer over Tempo."},
    {"name": "Metrics", "description": "PromQL-backed query layer over Prometheus + Pushgateway."},
    {
        "name": "Monitoring",
        "description": "Cross-service reachability/topology aggregation.",
    },
    {
        "name": "Alerts",
        "description": (
            "Operator-only alert query/action API over Alertmanager, plus real "
            "dynamic alert-rule CRUD over Prometheus."
        ),
    },
    {
        "name": "Fleet Health",
        "description": "Normalized /ready view over Tenent, APIGateway, and this service itself.",
    },
    {
        "name": "Observability",
        "description": (
            "Operator-only investigation/correlation API composing every domain above, in-process."
        ),
    },
]

RESPONSES_COMMON: dict[int | str, dict[str, Any]] = {
    403: {"description": "Operator (platform-admin) role required."},
}
