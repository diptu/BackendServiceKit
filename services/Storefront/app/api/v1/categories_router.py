"""Category endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.dependencies import CatalogServiceDep, TenantIdDep
from app.schemas.category import (
    CategoryListResponse,
    CategoryResponse,
    CreateCategoryRequest,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CreateCategoryRequest, tenant_id: TenantIdDep, svc: CatalogServiceDep
) -> CategoryResponse:
    return await svc.create_category(tenant_id, body)


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    tenant_id: TenantIdDep, svc: CatalogServiceDep
) -> CategoryListResponse:
    items = await svc.list_categories(tenant_id)
    return CategoryListResponse(items=items, total=len(items))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID, tenant_id: TenantIdDep, svc: CatalogServiceDep
) -> None:
    await svc.delete_category(tenant_id, category_id)
