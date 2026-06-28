"""Tenant ORM model — system of record for tenant master data."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    """Core tenant entity.

    Owns the canonical record for every customer on the platform.
    All other services reference tenant_id but never join to this table.
    """

    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','provisioning','active','suspended','archived','deleted')",
            name="valid_status",
        ),
        Index("idx_tenants_name", "name", unique=True),
        Index("idx_tenants_status_region", "status", "region"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Globally unique URL-safe slug.",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable tenant name.",
    )
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        comment="Current lifecycle state.",
    )

    region: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="en-US")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")

    owner_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Primary owner user_id (projection — not a FK to User Service).",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )
