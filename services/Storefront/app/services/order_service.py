"""Order business logic: checkout (cart -> order) and order lifecycle."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ORDER_TRANSITIONS, CartStatus, OrderStatus
from app.domain.exceptions import (
    CartNotFoundError,
    EmptyCartError,
    InvalidOrderStatusTransitionError,
    OrderNotFoundError,
    OutOfStockError,
    VariantNotFoundError,
)
from app.models.order import Order, OrderItem
from app.repositories.cart import CartRepository
from app.repositories.order import OrderRepository
from app.repositories.product import ProductRepository
from app.schemas.order import OrderItemResponse, OrderResponse


def _variant_label(size: str | None, color: str | None) -> str | None:
    parts = [p for p in (size, color) if p]
    return " / ".join(parts) if parts else None


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._carts = CartRepository(session)
        self._products = ProductRepository(session)

    async def checkout(
        self,
        tenant_id: UUID,
        cart_id: UUID,
        *,
        email: str | None = None,
        shipping_address: str | None = None,
    ) -> OrderResponse:
        cart = await self._carts.get_by_id(cart_id, tenant_id=tenant_id)
        if cart is None:
            raise CartNotFoundError(cart_id)
        items = await self._carts.list_items(cart.id)
        if not items:
            raise EmptyCartError()

        order = Order(
            tenant_id=tenant_id,
            customer_ref=cart.customer_ref,
            email=email,
            status=OrderStatus.PENDING.value,
            currency=cart.currency,
            shipping_address=shipping_address,
        )
        await self._orders.create(order)

        subtotal = 0
        for item in items:
            variant = await self._products.get_variant(
                item.variant_id, tenant_id=tenant_id
            )
            if variant is None:
                raise VariantNotFoundError(item.variant_id)
            if item.quantity > variant.stock_quantity:
                raise OutOfStockError(
                    variant.sku, item.quantity, variant.stock_quantity
                )
            product = await self._products.get_by_id(
                variant.product_id, tenant_id=tenant_id
            )
            product_name = product.name if product is not None else variant.sku

            await self._orders.add_item(
                OrderItem(
                    tenant_id=tenant_id,
                    order_id=order.id,
                    variant_id=variant.id,
                    product_name=product_name,
                    variant_label=_variant_label(variant.size, variant.color),
                    sku=variant.sku,
                    quantity=item.quantity,
                    unit_price_cents=item.unit_price_cents,
                )
            )
            variant.stock_quantity -= item.quantity
            subtotal += item.quantity * item.unit_price_cents

        order.subtotal_cents = subtotal
        order.total_cents = subtotal
        cart.status = CartStatus.CHECKED_OUT.value
        await self._session.flush()
        return await self._build_response(order)

    async def get_order(self, tenant_id: UUID, order_id: UUID) -> OrderResponse:
        order = await self._require_order(tenant_id, order_id)
        return await self._build_response(order)

    async def list_orders(
        self, tenant_id: UUID, *, customer_ref: str | None = None
    ) -> list[OrderResponse]:
        orders = await self._orders.list_orders(
            tenant_id=tenant_id, customer_ref=customer_ref
        )
        return [await self._build_response(o) for o in orders]

    async def update_status(
        self, tenant_id: UUID, order_id: UUID, new_status: OrderStatus
    ) -> OrderResponse:
        order = await self._require_order(tenant_id, order_id)
        current = OrderStatus(order.status)
        if new_status not in ORDER_TRANSITIONS[current]:
            raise InvalidOrderStatusTransitionError(current.value, new_status.value)
        order.status = new_status.value
        await self._session.flush()
        return await self._build_response(order)

    # ----- helpers ---------------------------------------------------------
    async def _require_order(self, tenant_id: UUID, order_id: UUID) -> Order:
        order = await self._orders.get_by_id(order_id, tenant_id=tenant_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    async def _build_response(self, order: Order) -> OrderResponse:
        # Reload server-managed columns (updated_at via onupdate) invalidated by
        # the preceding flush, so serialization doesn't lazy-load in sync context.
        await self._session.refresh(order)
        items = await self._orders.list_items(order.id)
        resp = OrderResponse.model_validate(order)
        resp.items = [
            OrderItemResponse(
                id=i.id,
                variant_id=i.variant_id,
                product_name=i.product_name,
                variant_label=i.variant_label,
                sku=i.sku,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
                line_total_cents=i.quantity * i.unit_price_cents,
            )
            for i in items
        ]
        return resp
