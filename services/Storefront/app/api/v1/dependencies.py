"""FastAPI shared dependencies for the Storefront service."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.dependencies import get_db
from app.services.cart_service import CartService
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService


async def get_tenant_id(
    x_tenant_id: Annotated[UUID | None, Header()] = None,
) -> UUID:
    if x_tenant_id is None:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required.")
    return x_tenant_id


async def get_catalog_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CatalogService:
    return CatalogService(db)


async def get_cart_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CartService:
    return CartService(db)


async def get_order_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderService:
    return OrderService(db)


DbDep = Annotated[AsyncSession, Depends(get_db)]
TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
