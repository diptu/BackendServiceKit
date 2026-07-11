"""Product + variant endpoints (catalog management + storefront reads)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.dependencies import CatalogServiceDep, TenantIdDep
from app.schemas.product import (
    CreateProductRequest,
    CreateVariantRequest,
    ProductListResponse,
    ProductResponse,
    UpdateProductRequest,
    VariantResponse,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    body: CreateProductRequest, tenant_id: TenantIdDep, svc: CatalogServiceDep
) -> ProductResponse:
    return await svc.create_product(tenant_id, body)


@router.get("", response_model=ProductListResponse)
async def list_products(
    tenant_id: TenantIdDep,
    svc: CatalogServiceDep,
    status: str | None = Query(None),
    category_id: UUID | None = Query(None),
) -> ProductListResponse:
    items = await svc.list_products(tenant_id, status=status, category_id=category_id)
    return ProductListResponse(items=items, total=len(items))


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID, tenant_id: TenantIdDep, svc: CatalogServiceDep
) -> ProductResponse:
    return await svc.get_product(tenant_id, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    body: UpdateProductRequest,
    tenant_id: TenantIdDep,
    svc: CatalogServiceDep,
) -> ProductResponse:
    return await svc.update_product(tenant_id, product_id, body)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID, tenant_id: TenantIdDep, svc: CatalogServiceDep
) -> None:
    await svc.delete_product(tenant_id, product_id)


@router.post("/{product_id}/variants", response_model=VariantResponse, status_code=201)
async def add_variant(
    product_id: UUID,
    body: CreateVariantRequest,
    tenant_id: TenantIdDep,
    svc: CatalogServiceDep,
) -> VariantResponse:
    return await svc.add_variant(tenant_id, product_id, body)


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
async def delete_variant(
    product_id: UUID,
    variant_id: UUID,
    tenant_id: TenantIdDep,
    svc: CatalogServiceDep,
) -> None:
    await svc.delete_variant(tenant_id, variant_id)
