"""OpenAPI metadata — tags and shared response schemas."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Authentication",
        "description": (
            "Identity verification only — never authorization. Credential "
            "issuance, login, JWT access tokens + opaque revocable refresh "
            "tokens, password change/reset, session listing/revocation. "
            "Every request is scoped by the `X-Tenant-ID` header. MFA, "
            "OAuth2/OIDC, and SSO are documented in README.md but not yet "
            "built — see TODO.md."
        ),
    },
    {
        "name": "Health",
        "description": "Liveness and readiness probes.",
    },
]
