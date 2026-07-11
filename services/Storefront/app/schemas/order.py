"""Order request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import OrderStatus
from app.schemas.base import AppBaseModel


class CheckoutRequest(AppBaseModel):
    cart_id: UUID
    email: str | None = Field(None, max_length=255)
    shipping_address: str | None = None


class UpdateOrderStatusRequest(AppBaseModel):
    status: OrderStatus


class OrderItemResponse(AppBaseModel):
    id: UUID
    variant_id: UUID
    product_name: str
    variant_label: str | None
    sku: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderResponse(AppBaseModel):
    id: UUID
    tenant_id: UUID
    customer_ref: str | None
    email: str | None
    status: str
    currency: str
    subtotal_cents: int
    total_cents: int
    shipping_address: str | None
    items: list[OrderItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class OrderListResponse(AppBaseModel):
    items: list[OrderResponse]
    total: int
