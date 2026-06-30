"""Health check endpoints — liveness + readiness with real dependency checks."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

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
    from app.infrastructure.cache.redis_cache import get_redis
    from app.infrastructure.database.session import SessionLocal
    from shared.observability.health.dependencies import check_postgres, check_redis
    from shared.observability.health.readiness import ReadinessChecker

    checker = ReadinessChecker()
    checker.add("postgres", lambda: check_postgres(SessionLocal))
    checker.add("redis", lambda: check_redis(get_redis()))

    result = await checker.check()
    status_code = 200 if result.status == "ok" else 503
    return JSONResponse(status_code=status_code, content=result.as_dict())
