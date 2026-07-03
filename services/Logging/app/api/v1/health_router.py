"""Health check endpoints — liveness + readiness with a real Loki probe."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_loki_client
from app.core.config import settings
from app.infrastructure.loki.loki_client import LokiClient

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health() -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "service": settings.app_name, "version": settings.app_version}
    )


@router.get("/ready", summary="Readiness probe")
async def ready(
    request: Request, loki: Annotated[LokiClient, Depends(get_loki_client)]
) -> JSONResponse:
    loki_ready = await loki.ready()
    status_code = 200 if loki_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if loki_ready else "degraded", "loki": loki_ready},
    )
