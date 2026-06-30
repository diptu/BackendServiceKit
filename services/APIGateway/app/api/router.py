"""Top-level API router — assembles versioned and infrastructure sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import gateway_router, health, proxy_router
from app.core.config import settings

api_router = APIRouter()

# 1. Liveness/readiness probes — registered first so /{full_path:path} doesn't shadow them
api_router.include_router(health.router)

# 2. Gateway management (routes, status)
api_router.include_router(gateway_router.router, prefix=settings.api_v1_prefix)

# 3. Catch-all reverse proxy — MUST be registered last
api_router.include_router(proxy_router.router)
