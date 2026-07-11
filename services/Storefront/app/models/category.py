"""Category ORM model — a grouping of products (e.g. "Dresses", "Outerwear")."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_categories_tenant_slug"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
