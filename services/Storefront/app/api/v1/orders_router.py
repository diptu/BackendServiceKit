"""Order endpoints — checkout and order lifecycle."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.dependencies import OrderServiceDep, TenantIdDep
from app.schemas.order import (
    CheckoutRequest,
    OrderListResponse,
    OrderResponse,
    UpdateOrderStatusRequest,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(
    body: CheckoutRequest, tenant_id: TenantIdDep, svc: OrderServiceDep
) -> OrderResponse:
    return await svc.checkout(
        tenant_id,
        body.cart_id,
        email=body.email,
        shipping_address=body.shipping_address,
    )


@router.get("", response_model=OrderListResponse)
async def list_orders(
    tenant_id: TenantIdDep,
    svc: OrderServiceDep,
    customer_ref: str | None = Query(None),
) -> OrderListResponse:
    items = await svc.list_orders(tenant_id, customer_ref=customer_ref)
    return OrderListResponse(items=items, total=len(items))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID, tenant_id: TenantIdDep, svc: OrderServiceDep
) -> OrderResponse:
    return await svc.get_order(tenant_id, order_id)


@router.post("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    body: UpdateOrderStatusRequest,
    tenant_id: TenantIdDep,
    svc: OrderServiceDep,
) -> OrderResponse:
    return await svc.update_status(tenant_id, order_id, body.status)
