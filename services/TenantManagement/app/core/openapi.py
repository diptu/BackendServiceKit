"""OpenAPI metadata constants — tags, descriptions, and reusable response objects."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Tag metadata (controls Swagger UI grouping and ordering)
# ---------------------------------------------------------------------------

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Tenants",
        "description": (
            "Core tenant CRUD operations. "
            "A **tenant** is an independent customer boundary on the platform "
            "(e.g. Alphabet, Meta). "
            "All other resources are scoped to a tenant. "
            "Tenant `name` (slug) is immutable after creation."
        ),
    },
    {
        "name": "Tenant Lifecycle",
        "description": (
            "Lifecycle state transitions for a tenant. "
            "Only **platform administrators** may trigger transitions. "
            "State changes are strictly enforced — invalid transitions return `409 Conflict`. "
            "\n\n"
            "**Valid transitions:**\n"
            "```\n"
            "draft → provisioning → active\n"
            "active → suspended → active  (reactivation)\n"
            "active | suspended → archived → deleted\n"
            "```\n"
            "The `deleted` state is terminal — no further transitions are permitted."
        ),
    },
    {
        "name": "Tenant Settings",
        "description": (
            "Per-tenant configuration: timezone, locale, language, date format, "
            "currency, session timeout, and UI theme. "
            "One settings record exists per tenant, created automatically on provisioning. "
            "Updates emit a `TenantConfigurationUpdated` domain event."
        ),
    },
    {
        "name": "Tenant Owners",
        "description": (
            "Manage the users who own or administer a tenant. "
            "Every tenant must retain at least one active owner at all times. "
            "Attempting to remove the last owner returns `422 Unprocessable Entity`. "
            "Ownership changes are fully audited."
        ),
    },
    {
        "name": "Tenant Metadata",
        "description": (
            "Store and retrieve arbitrary key-value metadata on a tenant "
            "(industry, company size, customer tier, internal notes, etc.). "
            "`PATCH` upserts keys — existing keys are overwritten, new keys are added. "
            "Metadata updates require no database schema changes."
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

# ---------------------------------------------------------------------------
# Reusable response objects for endpoint `responses={}` declarations
# ---------------------------------------------------------------------------

_TENANT_ID_EXAMPLE = "550e8400-e29b-41d4-a716-446655440000"

R_401: dict[str, Any] = {
    "description": "Unauthorized — missing or invalid bearer token.",
    "content": {"application/json": {"example": {"detail": "Not authenticated."}}},
}

R_403: dict[str, Any] = {
    "description": "Forbidden — caller lacks the required platform admin role.",
    "content": {
        "application/json": {
            "example": {"detail": "You do not have permission to perform this action."}
        }
    },
}

R_404: dict[str, Any] = {
    "description": "Not Found — no tenant exists with the given ID.",
    "content": {
        "application/json": {
            "example": {"detail": f"Tenant {_TENANT_ID_EXAMPLE} not found."}
        }
    },
}

R_409_CONFLICT: dict[str, Any] = {
    "description": (
        "Conflict — duplicate tenant name / slug, "
        "or the requested state transition is not permitted from the current state."
    ),
    "content": {
        "application/json": {
            "examples": {
                "name_conflict": {
                    "summary": "Tenant name already taken",
                    "value": {
                        "detail": "Tenant name 'alphabet-corp' is already taken."
                    },
                },
                "invalid_transition": {
                    "summary": "Invalid state transition",
                    "value": {
                        "detail": "Invalid tenant state transition: archived → active.",
                        "error_code": "INVALID_TENANT_STATE_TRANSITION",
                    },
                },
            }
        }
    },
}

R_423: dict[str, Any] = {
    "description": "Locked — tenant is archived and accepts no write operations.",
    "content": {
        "application/json": {
            "example": {
                "detail": f"Tenant {_TENANT_ID_EXAMPLE} is archived and read-only."
            }
        }
    },
}

# Common bundles for convenience
RESPONSES_READ: dict[int | str, dict[str, Any]] = {
    401: R_401,
    403: R_403,
    404: R_404,
}

RESPONSES_WRITE: dict[int | str, dict[str, Any]] = {
    401: R_401,
    403: R_403,
    404: R_404,
    409: R_409_CONFLICT,
    423: R_423,
}

RESPONSES_CREATE: dict[int | str, dict[str, Any]] = {
    401: R_401,
    403: R_403,
    409: R_409_CONFLICT,
}

RESPONSES_TRANSITION: dict[int | str, dict[str, Any]] = {
    401: R_401,
    403: R_403,
    404: R_404,
    409: R_409_CONFLICT,
}
