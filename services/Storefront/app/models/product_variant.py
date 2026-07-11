"""ProductVariant ORM model — a specific buyable option of a product.

For clothing this is the (size, color) combination that carries its own SKU
and stock level, e.g. "Willow Dress / M / Sage".
"""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_product_variants_tenant_sku"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    size: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # NULL price_cents means "inherit the product's base price".
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
