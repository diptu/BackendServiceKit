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
        "name": "Proxy — TenantManagement",
        "description": (
            "Reverse-proxy to **TenantManagement** (`/api/v1/tenants/*`). "
            "GET responses are cached in Redis for 5 minutes. "
            "Write operations invalidate the cache for the affected tenant."
        ),
    },
    {
        "name": "Proxy — TenantLifecycle",
        "description": (
            "Reverse-proxy to **TenantLifecycle** (`/api/v1/tenant-lifecycle/*`). "
            "History GET responses are cached in Redis for 60 seconds."
        ),
    },
]

RESPONSES_PROXY = {
    502: {"description": "Upstream service returned an unexpected error."},
    503: {"description": "Upstream service is unavailable."},
    504: {"description": "Upstream service did not respond within the timeout."},
}
