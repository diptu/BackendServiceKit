"""Main API router — assembles all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health_router import router as health_router
from app.api.v1.sessions_router import router as sessions_router
from app.api.v1.users_router import router as users_router

api_router = APIRouter()

# Health / readiness — no prefix (served at root)
api_router.include_router(health_router)

# Versioned resources
_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(sessions_router)
_v1.include_router(users_router)

api_router.include_router(_v1)
