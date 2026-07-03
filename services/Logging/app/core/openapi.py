"""OpenAPI tag metadata and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {
        "name": "Logs — Search",
        "description": (
            "Tenant-scoped read access to logs stored in Loki. Every query is "
            "translated to LogQL server-side — callers never write LogQL directly."
        ),
    },
    {
        "name": "Logs — Ingest",
        "description": (
            "Escape-hatch ingestion for emitters that cannot log to stdout under "
            "promtail's reach (browser/mobile clients, webhooks). Internal "
            "services should keep logging to stdout — that pipeline already "
            "ships to Loki via promtail with zero code here."
        ),
    },
    {
        "name": "Logs — Export",
        "description": "Streamed bulk export of a filtered log range.",
    },
]

RESPONSES_COMMON: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid bearer token."},
    403: {"description": "Caller's tenant scope does not permit this query."},
    503: {"description": "Loki is unreachable."},
}
