"""Main API router — assembles all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth_router import router as auth_router
from app.api.v1.health_router import router as health_router
from app.api.v1.oauth_router import router as oauth_router
from app.api.v1.sso_router import router as sso_router
from app.api.v1.well_known_router import router as well_known_router

api_router = APIRouter()

# Health / readiness — no prefix (served at root)
api_router.include_router(health_router)

# Discovery — served at root (/.well-known/jwks.json), not under /api/v1
api_router.include_router(well_known_router)

# Versioned resources
_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(auth_router)
_v1.include_router(oauth_router)
_v1.include_router(sso_router)

api_router.include_router(_v1)
