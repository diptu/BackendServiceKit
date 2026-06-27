"""OpenAPI metadata constants — tags, descriptions, and reusable response objects."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Lifecycle",
        "description": (
            "Tenant lifecycle state transitions. "
            "Only **platform administrators** may trigger transitions. "
            "Invalid transitions return `409 Conflict`.\n\n"
            "**Valid transitions:**\n"
            "```\n"
            "provisioning → active\n"
            "active   → suspended | locked | archived\n"
            "suspended → active | archived\n"
            "locked   → archived\n"
            "archived → deleted\n"
            "```\n"
            "The `deleted` state is terminal."
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

_TENANT_ID_EXAMPLE = "550e8400-e29b-41d4-a716-446655440000"

R_401: dict[str, Any] = {
    "description": "Unauthorized — missing or invalid bearer token.",
    "content": {
        "application/json": {"example": {"detail": "Not authenticated."}}
    },
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
    "description": "Not Found — no lifecycle record exists for this tenant ID.",
    "content": {
        "application/json": {
            "example": {
                "detail": f"No lifecycle record for tenant {_TENANT_ID_EXAMPLE}."
            }
        }
    },
}

R_409_CONFLICT: dict[str, Any] = {
    "description": "Conflict — the requested state transition is not permitted from the current state.",
    "content": {
        "application/json": {
            "example": {
                "detail": "Invalid lifecycle transition: archived → active.",
                "error_code": "INVALID_LIFECYCLE_TRANSITION",
            }
        }
    },
}

R_423: dict[str, Any] = {
    "description": "Locked — tenant is in a terminal or locked state.",
    "content": {
        "application/json": {
            "example": {
                "detail": f"Tenant {_TENANT_ID_EXAMPLE} is in a non-writable state."
            }
        }
    },
}

RESPONSES_READ: dict[int, dict[str, Any]] = {401: R_401, 403: R_403, 404: R_404}
RESPONSES_TRANSITION: dict[int, dict[str, Any]] = {
    401: R_401,
    403: R_403,
    404: R_404,
    409: R_409_CONFLICT,
}
