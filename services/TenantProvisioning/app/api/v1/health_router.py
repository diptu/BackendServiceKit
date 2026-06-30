"""Liveness and readiness probes with dependency checks."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe — checks DB, Redis, RabbitMQ",
)
async def ready() -> ReadinessResponse:
    checks: dict[str, str] = {}

    # Database check
    try:
        from app.infrastructure.database.session import SessionLocal
        async with SessionLocal() as session:
            await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=float(settings.healthcheck_timeout_seconds),
            )
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # Redis check
    try:
        from app.infrastructure.cache.redis_cache import get_redis
        await asyncio.wait_for(
            get_redis().ping(),
            timeout=float(settings.healthcheck_timeout_seconds),
        )
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # RabbitMQ check
    try:
        import aio_pika
        conn = await asyncio.wait_for(
            aio_pika.connect(settings.rabbitmq_url),
            timeout=float(settings.healthcheck_timeout_seconds),
        )
        await conn.close()
        checks["rabbitmq"] = "ok"
    except Exception as exc:
        checks["rabbitmq"] = f"error: {exc}"

    failed = {k: v for k, v in checks.items() if v != "ok"}
    if failed:
        logger.warning("readiness_check_failed", extra={"failed": str(failed)})
        raise HTTPException(
            status_code=503,
            detail={"status": "unavailable", "checks": checks},
        )

    return ReadinessResponse(status="ready", checks=checks)
