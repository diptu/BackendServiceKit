"""Order + OrderItem ORM models — an immutable record of a placed order.

Order items snapshot the product/variant details (name, SKU, price) so the
order stays accurate even if the catalog changes later.
"""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import OrderStatus
from app.infrastructure.database.base import Base, TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    customer_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OrderStatus.PENDING.value
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Kept as a plain reference (not a FK) so order history survives catalog deletes.
    variant_id: Mapped[UUID] = mapped_column(nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
