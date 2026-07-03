"""Top-level API router — aggregates all v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health_router import router as health_router
from app.api.v1.observability_router import router as observability_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(observability_router, prefix=settings.api_v1_prefix)
