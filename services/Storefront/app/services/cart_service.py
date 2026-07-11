"""Cart business logic: create carts, add/update/remove items, compute totals."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import (
    CartNotFoundError,
    OutOfStockError,
    VariantNotFoundError,
)
from app.models.cart import Cart, CartItem
from app.models.product_variant import ProductVariant
from app.repositories.cart import CartRepository
from app.repositories.product import ProductRepository
from app.schemas.cart import CartItemResponse, CartResponse, CreateCartRequest


class CartService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._carts = CartRepository(session)
        self._products = ProductRepository(session)

    async def create_cart(
        self, tenant_id: UUID, req: CreateCartRequest
    ) -> CartResponse:
        cart = Cart(
            tenant_id=tenant_id,
            customer_ref=req.customer_ref,
            currency=req.currency,
        )
        await self._carts.create(cart)
        return await self._build_response(cart)

    async def get_cart(self, tenant_id: UUID, cart_id: UUID) -> CartResponse:
        cart = await self._require_cart(tenant_id, cart_id)
        return await self._build_response(cart)

    async def add_item(
        self, tenant_id: UUID, cart_id: UUID, variant_id: UUID, quantity: int
    ) -> CartResponse:
        cart = await self._require_cart(tenant_id, cart_id)
        variant = await self._require_variant(tenant_id, variant_id)
        unit_price = await self._unit_price(tenant_id, variant)

        existing = await self._carts.get_item(cart.id, variant_id)
        desired = quantity + (existing.quantity if existing else 0)
        self._assert_stock(variant, desired)

        if existing is not None:
            existing.quantity = desired
            existing.unit_price_cents = unit_price
            await self._session.flush()
        else:
            await self._carts.add_item(
                CartItem(
                    tenant_id=tenant_id,
                    cart_id=cart.id,
                    variant_id=variant_id,
                    quantity=quantity,
                    unit_price_cents=unit_price,
                )
            )
        return await self._build_response(cart)

    async def update_item(
        self, tenant_id: UUID, cart_id: UUID, item_id: UUID, quantity: int
    ) -> CartResponse:
        cart = await self._require_cart(tenant_id, cart_id)
        item = await self._carts.get_item_by_id(item_id, tenant_id=tenant_id)
        if item is None or item.cart_id != cart.id:
            raise CartNotFoundError(cart_id)
        variant = await self._require_variant(tenant_id, item.variant_id)
        self._assert_stock(variant, quantity)
        item.quantity = quantity
        await self._session.flush()
        return await self._build_response(cart)

    async def remove_item(
        self, tenant_id: UUID, cart_id: UUID, item_id: UUID
    ) -> CartResponse:
        cart = await self._require_cart(tenant_id, cart_id)
        item = await self._carts.get_item_by_id(item_id, tenant_id=tenant_id)
        if item is not None and item.cart_id == cart.id:
            await self._carts.delete_item(item)
        return await self._build_response(cart)

    # ----- helpers ---------------------------------------------------------
    async def _require_cart(self, tenant_id: UUID, cart_id: UUID) -> Cart:
        cart = await self._carts.get_by_id(cart_id, tenant_id=tenant_id)
        if cart is None:
            raise CartNotFoundError(cart_id)
        return cart

    async def _require_variant(
        self, tenant_id: UUID, variant_id: UUID
    ) -> ProductVariant:
        variant = await self._products.get_variant(variant_id, tenant_id=tenant_id)
        if variant is None:
            raise VariantNotFoundError(variant_id)
        return variant

    async def _unit_price(self, tenant_id: UUID, variant: ProductVariant) -> int:
        if variant.price_cents is not None:
            return variant.price_cents
        product = await self._products.get_by_id(
            variant.product_id, tenant_id=tenant_id
        )
        return product.price_cents if product is not None else 0

    @staticmethod
    def _assert_stock(variant: ProductVariant, desired: int) -> None:
        if desired > variant.stock_quantity:
            raise OutOfStockError(variant.sku, desired, variant.stock_quantity)

    async def _build_response(self, cart: Cart) -> CartResponse:
        await self._session.refresh(cart)
        items = await self._carts.list_items(cart.id)
        item_resps = [
            CartItemResponse(
                id=i.id,
                variant_id=i.variant_id,
                quantity=i.quantity,
                unit_price_cents=i.unit_price_cents,
                line_total_cents=i.quantity * i.unit_price_cents,
            )
            for i in items
        ]
        subtotal = sum(r.line_total_cents for r in item_resps)
        resp = CartResponse.model_validate(cart)
        resp.items = item_resps
        resp.subtotal_cents = subtotal
        return resp
