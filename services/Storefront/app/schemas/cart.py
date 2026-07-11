"""Cart request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import AppBaseModel


class CreateCartRequest(AppBaseModel):
    customer_ref: str | None = Field(None, max_length=255)
    currency: str = Field("USD", min_length=3, max_length=3)


class AddCartItemRequest(AppBaseModel):
    variant_id: UUID
    quantity: int = Field(1, ge=1)


class UpdateCartItemRequest(AppBaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(AppBaseModel):
    id: UUID
    variant_id: UUID
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class CartResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    customer_ref: str | None
    status: str
    currency: str
    items: list[CartItemResponse] = Field(default_factory=list)
    subtotal_cents: int = 0
    created_at: datetime
    updated_at: datetime
