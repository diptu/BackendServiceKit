"""Health check endpoints — liveness + readiness with a real Tempo probe."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_tempo_client
from app.core.config import settings
from app.infrastructure.tempo.tempo_client import TempoClient

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health() -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "service": settings.app_name, "version": settings.app_version}
    )


@router.get("/ready", summary="Readiness probe")
async def ready(
    request: Request, tempo: Annotated[TempoClient, Depends(get_tempo_client)]
) -> JSONResponse:
    tempo_ready = await tempo.ready()
    status_code = 200 if tempo_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if tempo_ready else "degraded", "tempo": tempo_ready},
    )
