"""OpenAPI metadata — tags for every resource group."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Users",
        "description": (
            "Read-only projection of identities synced from the User Service. "
            "Every request is scoped by the `X-Tenant-ID` header."
        ),
    },
    {"name": "Roles", "description": "Named, tenant-scoped bundles of permissions."},
    {"name": "Permissions", "description": "Named, tenant-scoped capabilities."},
    {"name": "Groups", "description": "Tenant-scoped collections of users."},
    {
        "name": "Tenant Memberships",
        "description": "A user's membership within a tenant.",
    },
    {"name": "Attributes", "description": "ABAC key/value data attached to a user."},
    {
        "name": "Entitlements",
        "description": "What a user is granted, as opposed to what they can do.",
    },
    {
        "name": "Access Reviews",
        "description": "Access-governance reviews tracked to a decision.",
    },
    {"name": "Health", "description": "Liveness and readiness probes."},
]
