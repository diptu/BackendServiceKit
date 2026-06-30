"""OpenAPI metadata — merged tags from all three services."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Tenants",
        "description": (
            "Core tenant CRUD operations. "
            "A **tenant** is an independent customer boundary on the platform. "
            "All other resources are scoped to a tenant. "
            "Tenant `name` (slug) is immutable after creation."
        ),
    },
    {
        "name": "Tenant Lifecycle",
        "description": (
            "TM-facing lifecycle transitions (draft → provisioning → pending → active, etc.). "
            "State changes are strictly enforced — invalid transitions return `409 Conflict`."
        ),
    },
    {
        "name": "Lifecycle",
        "description": (
            "TL-authoritative state machine. Drives all lifecycle transitions with full event "
            "history. Supports provisioning, pending, activate, suspend, lock, archive, delete."
        ),
    },
    {
        "name": "Isolation",
        "description": (
            "Cross-tenant access enforcement. Validates resource ownership, checks access "
            "policies, manages resource claims, and logs access decisions."
        ),
    },
    {
        "name": "Tenant Settings",
        "description": "Per-tenant configuration: timezone, locale, language, currency, etc.",
    },
    {
        "name": "Tenant Owners",
        "description": "Manage users who own or administer a tenant.",
    },
    {
        "name": "Tenant Metadata",
        "description": "Arbitrary key-value metadata on a tenant.",
    },
    {
        "name": "Health",
        "description": "Liveness and readiness probes.",
    },
]

_TENANT_ID_EXAMPLE = "550e8400-e29b-41d4-a716-446655440000"

R_401: dict[str, Any] = {
    "description": "Unauthorized — missing or invalid bearer token.",
    "content": {"application/json": {"example": {"detail": "Not authenticated."}}},
}

R_403: dict[str, Any] = {
    "description": "Forbidden.",
    "content": {"application/json": {"example": {"detail": "Access denied."}}},
}

R_404: dict[str, Any] = {
    "description": "Not Found.",
    "content": {
        "application/json": {
            "example": {"detail": f"Tenant {_TENANT_ID_EXAMPLE} not found."}
        }
    },
}

R_409_CONFLICT: dict[str, Any] = {
    "description": "Conflict — duplicate name or invalid state transition.",
    "content": {"application/json": {"example": {"detail": "Conflict."}}},
}

R_423: dict[str, Any] = {
    "description": "Locked — tenant is archived and read-only.",
    "content": {
        "application/json": {
            "example": {"detail": f"Tenant {_TENANT_ID_EXAMPLE} is archived and read-only."}
        }
    },
}

RESPONSES_READ: dict[int | str, dict[str, Any]] = {401: R_401, 403: R_403, 404: R_404}
RESPONSES_WRITE: dict[int | str, dict[str, Any]] = {401: R_401, 403: R_403, 404: R_404, 409: R_409_CONFLICT, 423: R_423}
RESPONSES_CREATE: dict[int | str, dict[str, Any]] = {401: R_401, 403: R_403, 409: R_409_CONFLICT}
RESPONSES_TRANSITION: dict[int | str, dict[str, Any]] = {401: R_401, 403: R_403, 404: R_404, 409: R_409_CONFLICT}
