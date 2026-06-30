"""OpenAPI metadata — tags and shared response schemas."""

from __future__ import annotations

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Liveness and readiness probes for the API Gateway.",
    },
    {
        "name": "Gateway",
        "description": "Gateway management: route registry, cache stats, upstream health.",
    },
    {
        "name": "Proxy — Tenent",
        "description": (
            "Reverse-proxy to the **Tenent** combined service. Handles:\n\n"
            "- `/api/v1/tenants/*` — tenant CRUD, settings, owners, metadata, TM-side lifecycle transitions. "
            "GET responses cached 5 minutes.\n"
            "- `/api/v1/lifecycle/*` — authoritative state machine (provision → pending → active, "
            "suspend, lock, archive, delete). GET history cached 5 minutes.\n"
            "- `/api/v1/isolation/*` — cross-tenant access enforcement, resource claims, "
            "policy management. Decision GETs cached 60 seconds.\n\n"
            "Write operations with `X-Tenant-ID` header invalidate the per-tenant cache."
        ),
    },
    {
        "name": "Proxy — TenantProvisioning",
        "description": (
            "Reverse-proxy to **TenantProvisioning** (`/api/v1/provisioning/*`). "
            "Celery-backed async infra-setup jobs. GET responses cached 30 seconds."
        ),
    },
    {
        "name": "Kong",
        "description": (
            "Kong API Gateway integration. Inspect Kong services, routes, and plugins "
            "via the Kong Admin API, and sync the FastAPI route registry into Kong dynamically."
        ),
    },
]

RESPONSES_PROXY = {
    502: {"description": "Upstream service returned an unexpected error."},
    503: {"description": "Upstream service is unavailable."},
    504: {"description": "Upstream service did not respond within the timeout."},
}
