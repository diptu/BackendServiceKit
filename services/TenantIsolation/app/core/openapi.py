"""OpenAPI metadata — tags, descriptions, and reusable response objects."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Isolation",
        "description": (
            "Tenant isolation enforcement — policy-based validation of cross-tenant access. "
            "`POST /isolation/validate` checks a batch of resource IDs against the caller's tenant. "
            "`POST /isolation/check-access` returns an ALLOW/DENY decision for a specific action. "
            "All decisions are cached in Redis and audited in the access decision log."
        ),
    },
    {
        "name": "Health",
        "description": (
            "Liveness and readiness probes. "
            "`GET /health` confirms the process is alive. "
            "`GET /ready` confirms all dependencies are reachable."
        ),
    },
]

R_401: dict[str, Any] = {
    "description": "Unauthorized — missing or invalid bearer token.",
    "content": {"application/json": {"example": {"detail": "Missing bearer token."}}},
}

R_403: dict[str, Any] = {
    "description": "Forbidden — cross-tenant isolation violation.",
    "content": {
        "application/json": {
            "example": {
                "detail": "Cross-tenant access denied.",
                "error_code": "ISOLATION_VIOLATION",
            }
        }
    },
}

R_404: dict[str, Any] = {
    "description": "Not Found.",
    "content": {"application/json": {"example": {"detail": "Resource not found."}}},
}

R_409: dict[str, Any] = {
    "description": "Conflict — resource already claimed by a different tenant.",
    "content": {
        "application/json": {
            "example": {
                "detail": "Resource already claimed by another tenant.",
                "error_code": "RESOURCE_CLAIM_CONFLICT",
            }
        }
    },
}

RESPONSES_READ: dict[int, dict[str, Any]] = {401: R_401, 404: R_404}
RESPONSES_WRITE: dict[int, dict[str, Any]] = {401: R_401, 404: R_404, 409: R_409}
