"""OpenAPI metadata — tags and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Users",
        "description": (
            "Platform identity CRUD and status lifecycle "
            "(pending → active ⇄ suspended → deactivated). "
            "Every request is scoped by the `X-Tenant-ID` header."
        ),
    },
    {
        "name": "Platform Invitations",
        "description": (
            "Onboards a brand-new person onto the platform — accepting one "
            "creates a User row. Distinct from OrganizationManagement's "
            "invitations, which add an already-known user_id to a specific "
            "organization with a role."
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
    "description": "Conflict — duplicate email within the tenant, or invalid status transition.",
    "content": {"application/json": {"example": {"detail": "Conflict."}}},
}

RESPONSES_READ: dict[int | str, dict[str, Any]] = {400: R_400, 404: R_404}
RESPONSES_WRITE: dict[int | str, dict[str, Any]] = {400: R_400, 404: R_404, 409: R_409}
