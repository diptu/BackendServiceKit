"""Health check endpoints — liveness + readiness."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.infrastructure.database.session import SessionLocal

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        }
    )


@router.get("/ready", summary="Readiness probe")
async def ready() -> JSONResponse:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — report unhealthy, don't crash
        return JSONResponse(
            status_code=503, content={"status": "error", "detail": str(exc)}
        )
    return JSONResponse({"status": "ok"})
