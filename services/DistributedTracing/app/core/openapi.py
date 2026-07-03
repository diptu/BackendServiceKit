"""OpenAPI tag metadata and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {
        "name": "Traces — Search",
        "description": (
            "Operator-only read access to traces stored in Tempo (see "
            "TODO.md Decision #3 — spans carry no tenant identity today, so "
            "this service is not a tenant-self-service tier the way "
            "Logging's `/logs/*` endpoints are). Every query is translated "
            "to TraceQL server-side — callers never write TraceQL directly."
        ),
    },
    {
        "name": "Traces — Export",
        "description": "Streamed bulk export of a filtered trace range.",
    },
]

RESPONSES_COMMON: dict[int | str, dict[str, Any]] = {
    403: {"description": "Operator (platform-admin) role required."},
    503: {"description": "Tempo is unreachable."},
}
