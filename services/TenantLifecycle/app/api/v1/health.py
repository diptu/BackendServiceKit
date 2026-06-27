"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Liveness probe",
    description="""\
Confirms the service process is alive.

Used by the platform orchestrator (Kubernetes) to determine whether to restart
the container. Does **not** check downstream dependencies.
""",
    responses={
        200: {
            "description": "Service is alive.",
            "content": {"application/json": {"example": {"status": "ok"}}},
        }
    },
)
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="""\
Confirms the service is ready to accept traffic.

Checks that all required dependencies (database, message broker) are reachable
before returning `200 OK`.
""",
    responses={
        200: {
            "description": "Service is ready.",
            "content": {"application/json": {"example": {"status": "ready"}}},
        },
        503: {
            "description": "Service Unavailable — one or more dependencies are unreachable.",
            "content": {
                "application/json": {
                    "example": {"status": "not ready", "detail": "Database unreachable."}
                }
            },
        },
    },
)
async def ready() -> dict[str, Any]:
    return {"status": "ready"}
