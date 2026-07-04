"""This service's own liveness + readiness probes — one for the whole
merged process, not seven (TODO.md Decision #1's Phase 1.0)."""

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
