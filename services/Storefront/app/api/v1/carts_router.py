"""Cart endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.v1.dependencies import CartServiceDep, TenantIdDep
from app.schemas.cart import (
    AddCartItemRequest,
    CartResponse,
    CreateCartRequest,
    UpdateCartItemRequest,
)

router = APIRouter(prefix="/carts", tags=["Cart"])


@router.post("", response_model=CartResponse, status_code=201)
async def create_cart(
    body: CreateCartRequest, tenant_id: TenantIdDep, svc: CartServiceDep
) -> CartResponse:
    return await svc.create_cart(tenant_id, body)


@router.get("/{cart_id}", response_model=CartResponse)
async def get_cart(
    cart_id: UUID, tenant_id: TenantIdDep, svc: CartServiceDep
) -> CartResponse:
    return await svc.get_cart(tenant_id, cart_id)


@router.post("/{cart_id}/items", response_model=CartResponse, status_code=201)
async def add_item(
    cart_id: UUID,
    body: AddCartItemRequest,
    tenant_id: TenantIdDep,
    svc: CartServiceDep,
) -> CartResponse:
    return await svc.add_item(tenant_id, cart_id, body.variant_id, body.quantity)


@router.patch("/{cart_id}/items/{item_id}", response_model=CartResponse)
async def update_item(
    cart_id: UUID,
    item_id: UUID,
    body: UpdateCartItemRequest,
    tenant_id: TenantIdDep,
    svc: CartServiceDep,
) -> CartResponse:
    return await svc.update_item(tenant_id, cart_id, item_id, body.quantity)


@router.delete("/{cart_id}/items/{item_id}", response_model=CartResponse)
async def remove_item(
    cart_id: UUID, item_id: UUID, tenant_id: TenantIdDep, svc: CartServiceDep
) -> CartResponse:
    return await svc.remove_item(tenant_id, cart_id, item_id)
