"""Main API router — assembles all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.carts_router import router as carts_router
from app.api.v1.categories_router import router as categories_router
from app.api.v1.health_router import router as health_router
from app.api.v1.orders_router import router as orders_router
from app.api.v1.products_router import router as products_router

api_router = APIRouter()

# Health / readiness — no prefix (served at root)
api_router.include_router(health_router)

# Versioned resources
_v1 = APIRouter(prefix="/api/v1")
_v1.include_router(categories_router)
_v1.include_router(products_router)
_v1.include_router(carts_router)
_v1.include_router(orders_router)

api_router.include_router(_v1)
