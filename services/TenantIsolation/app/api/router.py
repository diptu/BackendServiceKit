"""Top-level API router."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.v1 import health_router as health
from app.api.v1 import isolation_router as isolation
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(isolation.router, prefix=settings.api_v1_prefix)


@api_router.get("/metrics", include_in_schema=False, tags=["Observability"])
async def metrics() -> Response:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST  # type: ignore[import-untyped]
    from app.core.metrics import REGISTRY
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
