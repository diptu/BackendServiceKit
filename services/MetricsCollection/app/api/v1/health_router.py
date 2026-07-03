"""Health check endpoints — liveness + readiness with a real Prometheus probe."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import get_prometheus_client
from app.core.config import settings
from app.infrastructure.prometheus.prometheus_client import PrometheusClient

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health() -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "service": settings.app_name, "version": settings.app_version}
    )


@router.get("/ready", summary="Readiness probe")
async def ready(
    request: Request, prometheus: Annotated[PrometheusClient, Depends(get_prometheus_client)]
) -> JSONResponse:
    prometheus_ready = await prometheus.ready()
    status_code = 200 if prometheus_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if prometheus_ready else "degraded",
            "prometheus": prometheus_ready,
        },
    )
