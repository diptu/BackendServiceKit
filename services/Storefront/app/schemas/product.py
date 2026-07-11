"""Product and variant request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import ProductStatus
from app.schemas.base import AppBaseModel


class CreateVariantRequest(AppBaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    size: str | None = Field(None, max_length=32)
    color: str | None = Field(None, max_length=64)
    price_cents: int | None = Field(None, ge=0)
    stock_quantity: int = Field(0, ge=0)


class VariantResponse(AppBaseModel):
    id: UUID
    product_id: UUID
    sku: str
    size: str | None
    color: str | None
    price_cents: int | None
    stock_quantity: int
    created_at: datetime
    updated_at: datetime


class CreateProductRequest(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str | None = None
    image_url: str | None = Field(None, max_length=2048)
    price_cents: int = Field(0, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    status: ProductStatus = ProductStatus.DRAFT
    category_id: UUID | None = None
    variants: list[CreateVariantRequest] = Field(default_factory=list)


class UpdateProductRequest(AppBaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    image_url: str | None = Field(None, max_length=2048)
    price_cents: int | None = Field(None, ge=0)
    status: ProductStatus | None = None
    category_id: UUID | None = None


class ProductResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    category_id: UUID | None
    name: str
    slug: str
    description: str | None
    image_url: str | None
    price_cents: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    variants: list[VariantResponse] = Field(default_factory=list)


class ProductListResponse(AppBaseModel):
    items: list[ProductResponse]
    total: int
