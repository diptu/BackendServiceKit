"""Tenant-scoped data access for orders and order items."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.order import Order, OrderItem
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    async def create(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    async def add_item(self, item: OrderItem) -> OrderItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_id(self, order_id: UUID, *, tenant_id: UUID) -> Order | None:
        stmt = select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_orders(
        self, *, tenant_id: UUID, customer_ref: str | None = None
    ) -> list[Order]:
        stmt = select(Order).where(Order.tenant_id == tenant_id)
        if customer_ref is not None:
            stmt = stmt.where(Order.customer_ref == customer_ref)
        stmt = stmt.order_by(Order.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_items(self, order_id: UUID) -> list[OrderItem]:
        stmt = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())
