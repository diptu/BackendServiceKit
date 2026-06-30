"""Liveness (/health) and readiness (/ready) endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.gateway import HealthResponse, ReadyResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns `200 ok` whenever the API Gateway process is running.",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Returns `200 ready` when Redis **and** RabbitMQ are reachable. "
        "Returns `503 degraded` with per-dependency status when one or both are down."
    ),
)
async def ready(request: Request) -> JSONResponse:
    redis_client = getattr(request.app.state, "redis", None)
    rabbitmq_conn = getattr(request.app.state, "rabbitmq_connection", None)

    redis_ok = False
    if redis_client is not None:
        try:
            redis_ok = bool(await redis_client.ping())
        except Exception:
            redis_ok = False

    rabbitmq_ok = rabbitmq_conn is not None and not rabbitmq_conn.is_closed

    overall = "ready" if (redis_ok and rabbitmq_ok) else "degraded"
    status_code = 200 if overall == "ready" else 503

    body = ReadyResponse(
        status=overall,
        redis="ok" if redis_ok else "unavailable",
        rabbitmq="ok" if rabbitmq_ok else "unavailable",
    )
    return JSONResponse(content=body.model_dump(), status_code=status_code)
