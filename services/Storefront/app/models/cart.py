"""Cart + CartItem ORM models — a shopper's in-progress selection."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import CartStatus
from app.infrastructure.database.base import Base, TimestampMixin


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    # Who the cart belongs to: a customer user_id, email, or anonymous session id.
    customer_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CartStatus.OPEN.value
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


class CartItem(TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_items_cart_variant"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    cart_id: Mapped[UUID] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Price captured when the item was added (may drift from the live price).
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
