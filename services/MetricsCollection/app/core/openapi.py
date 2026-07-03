"""OpenAPI tag metadata and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {
        "name": "Metrics — Query",
        "description": (
            "Operator-only read access to metrics scraped by Prometheus "
            "(see TODO.md Decision #3 — no metric carries a tenant identity "
            "today, so this is not a tenant-self-service tier). Every query "
            "is translated to PromQL server-side — callers never write "
            "PromQL directly."
        ),
    },
    {
        "name": "Metrics — Push",
        "description": (
            "Escape hatch for short-lived/batch processes that can't be "
            "scraped (e.g. Celery workers) — proxies to Pushgateway, a "
            "separate store from Prometheus's own scraped series (see "
            "TODO.md Decision #4). Not for long-running FastAPI services — "
            "those are already scraped directly with zero code here."
        ),
    },
]

RESPONSES_COMMON: dict[int | str, dict[str, Any]] = {
    403: {"description": "Operator (platform-admin) role required."},
    503: {"description": "Prometheus or Pushgateway is unreachable."},
}
