"""Tenant-scoped data access for carts and cart items."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.domain.enums import CartStatus
from app.models.cart import Cart, CartItem
from app.repositories.base import BaseRepository


class CartRepository(BaseRepository[Cart]):
    async def create(self, cart: Cart) -> Cart:
        self._session.add(cart)
        await self._session.flush()
        return cart

    async def get_by_id(self, cart_id: UUID, *, tenant_id: UUID) -> Cart | None:
        stmt = select(Cart).where(Cart.id == cart_id, Cart.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_open_for_customer(
        self, customer_ref: str, *, tenant_id: UUID
    ) -> Cart | None:
        stmt = select(Cart).where(
            Cart.tenant_id == tenant_id,
            Cart.customer_ref == customer_ref,
            Cart.status == CartStatus.OPEN.value,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_items(self, cart_id: UUID) -> list[CartItem]:
        stmt = (
            select(CartItem)
            .where(CartItem.cart_id == cart_id)
            .order_by(CartItem.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_item(self, cart_id: UUID, variant_id: UUID) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.cart_id == cart_id, CartItem.variant_id == variant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_item_by_id(
        self, item_id: UUID, *, tenant_id: UUID
    ) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.id == item_id, CartItem.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_item(self, item: CartItem) -> CartItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def delete_item(self, item: CartItem) -> None:
        await self._session.delete(item)
        await self._session.flush()
