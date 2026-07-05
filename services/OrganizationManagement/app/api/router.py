"""Main API router — assembles all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health_router import router as health_router
from app.api.v1.organizations_router import invitations_router
from app.api.v1.organizations_router import router as organizations_router

api_router = APIRouter()

# Health / readiness — no prefix (served at root)
api_router.include_router(health_router)

# Versioned resources
_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(organizations_router)
_v1.include_router(invitations_router)

api_router.include_router(_v1)
