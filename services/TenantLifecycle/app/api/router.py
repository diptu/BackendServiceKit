"""Top-level API router — assembles all versioned sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health_router, lifecycle_router
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(health_router.router)
api_router.include_router(lifecycle_router.router, prefix=settings.api_v1_prefix)
