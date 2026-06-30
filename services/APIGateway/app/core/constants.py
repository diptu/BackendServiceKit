"""Application-wide constants."""

from __future__ import annotations

# Cache key prefix for all gateway-managed entries
CACHE_KEY_PREFIX = "gw"

# Header forwarded to upstreams to identify the gateway
GATEWAY_HEADER = "X-Gateway-Version"

# Request-id header (propagated to upstreams for distributed tracing)
REQUEST_ID_HEADER = "X-Request-ID"

# Tenant-id header forwarded to and from upstreams
TENANT_ID_HEADER = "X-Tenant-ID"

# HTTP methods whose responses are eligible for caching
CACHEABLE_METHODS = frozenset({"GET"})

# HTTP methods that should trigger cache invalidation
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Headers that must NOT be forwarded to upstreams (hop-by-hop)
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
    }
)
