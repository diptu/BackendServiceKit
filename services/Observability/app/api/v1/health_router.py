"""This service's own liveness + readiness probes.

No hard dependency to gate readiness on — same reasoning as Monitoring's/
Alerting's/HealthCheck's equivalent (this service holds no credentials of
its own, per TODO.md Decision #11).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ok"}
