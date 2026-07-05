"""OpenAPI metadata — tags and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Profiles",
        "description": (
            "User metadata beyond identity/access: bio, preferences, "
            "avatar, contact info. Does not own first_name/last_name — "
            "those stay in UserManagement. Every request is scoped by the "
            "`X-Tenant-ID` header."
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
    "description": "Not Found — UserManagement doesn't have this user.",
    "content": {
        "application/json": {
            "example": {"detail": f"User {_USER_ID_EXAMPLE} not found."}
        }
    },
}

R_503: dict[str, Any] = {
    "description": "Service Unavailable — could not reach UserManagement.",
    "content": {
        "application/json": {"example": {"detail": "UserManagement is unreachable."}}
    },
}

RESPONSES_READ: dict[int | str, dict[str, Any]] = {400: R_400}
RESPONSES_WRITE: dict[int | str, dict[str, Any]] = {400: R_400, 404: R_404, 503: R_503}
