"""Product ORM model — a sellable item in a shop's catalog."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ProductStatus
from app.infrastructure.database.base import Base, TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_products_tenant_slug"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Money is stored as an integer number of minor units (cents) to avoid
    # floating-point rounding. Variants may override this base price.
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProductStatus.DRAFT.value
    )
