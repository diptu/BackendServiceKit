"""OpenAPI metadata — tags, descriptions, and reusable response objects."""

from __future__ import annotations

from typing import Any

TAGS_METADATA: list[dict[str, Any]] = [
    {
        "name": "Provisioning",
        "description": (
            "Tenant infrastructure provisioning jobs. "
            "Each job runs 8 sequential steps: schema creation, storage, "
            "default roles/permissions, admin user, workspace, feature flags, and finalization. "
            "A `POST /provisioning/tenants` starts a new job; "
            "`GET /provisioning/jobs/{job_id}` polls its status. "
            "Failed jobs can be retried via `POST /provisioning/tenants/{tenant_id}/retry`."
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

R_404: dict[str, Any] = {
    "description": "Not Found.",
    "content": {"application/json": {"example": {"detail": "Provisioning job not found."}}},
}

R_409: dict[str, Any] = {
    "description": "Conflict — an active provisioning job already exists for this tenant.",
    "content": {
        "application/json": {
            "example": {
                "detail": "An active provisioning job already exists for this tenant.",
                "error_code": "PROVISIONING_JOB_ALREADY_ACTIVE",
            }
        }
    },
}

RESPONSES_READ: dict[int, dict[str, Any]] = {404: R_404}
RESPONSES_WRITE: dict[int, dict[str, Any]] = {404: R_404, 409: R_409}
