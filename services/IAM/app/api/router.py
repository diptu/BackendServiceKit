"""Main API router — assembles all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.access_reviews_router import router as access_reviews_router
from app.api.v1.attributes_router import router as attributes_router
from app.api.v1.audit_events_router import router as audit_events_router
from app.api.v1.entitlements_router import router as entitlements_router
from app.api.v1.groups_router import router as groups_router
from app.api.v1.health_router import router as health_router
from app.api.v1.memberships_router import router as memberships_router
from app.api.v1.permissions_router import router as permissions_router
from app.api.v1.roles_router import router as roles_router
from app.api.v1.users_router import router as users_router

api_router = APIRouter()

# Health / readiness — no prefix (served at root)
api_router.include_router(health_router)

# Versioned resources
_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(users_router)
_v1.include_router(roles_router)
_v1.include_router(permissions_router)
_v1.include_router(groups_router)
_v1.include_router(memberships_router)
_v1.include_router(attributes_router)
_v1.include_router(entitlements_router)
_v1.include_router(access_reviews_router)
_v1.include_router(audit_events_router)

api_router.include_router(_v1)
