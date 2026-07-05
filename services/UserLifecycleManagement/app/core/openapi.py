"""OpenAPI metadata — tags and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "User Lifecycle",
        "description": (
            "State-machine orchestration for a user's lifecycle beyond "
            "UserManagement's own pending/active/suspended/deactivated "
            "states: locked (security hold), restore (undo a soft-delete), "
            "and onboard/offboard as named, audited variants of "
            "activate/deactivate. Calls into UserManagement for the "
            "underlying user record — does not duplicate its CRUD. Every "
            "request is scoped by the `X-Tenant-ID` header."
        ),
    },
    {
        "name": "Health",
        "description": "Liveness and readiness probes.",
    },
]

_USER_ID_EXAMPLE = "550e8400-e29b-41d4-a716-446655440000"

R_400: dict[str, Any] = {
    "description": "Bad Request — missing X-Tenant-ID header.",
    "content": {
        "application/json": {"example": {"detail": "X-Tenant-ID header is required."}}
    },
}

R_404: dict[str, Any] = {
    "description": "Not Found.",
    "content": {
        "application/json": {
            "example": {"detail": f"User {_USER_ID_EXAMPLE} not found."}
        }
    },
}

R_409: dict[str, Any] = {
    "description": "Conflict — invalid lifecycle transition, or user is not deleted.",
    "content": {"application/json": {"example": {"detail": "Conflict."}}},
}

R_503: dict[str, Any] = {
    "description": "Service Unavailable — could not reach UserManagement.",
    "content": {
        "application/json": {"example": {"detail": "UserManagement is unreachable."}}
    },
}

RESPONSES_READ: dict[int | str, dict[str, Any]] = {400: R_400, 404: R_404, 503: R_503}
RESPONSES_WRITE: dict[int | str, dict[str, Any]] = {
    400: R_400,
    404: R_404,
    409: R_409,
    503: R_503,
}
