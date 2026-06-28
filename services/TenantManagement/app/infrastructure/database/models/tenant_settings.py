"""TenantSettings ORM model — per-tenant configuration."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TenantSettings(Base):
    """Stores tenant-scoped configuration (one row per tenant)."""

    __tablename__ = "tenant_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="en-US")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="en")
    date_format: Mapped[str] = mapped_column(
        String(50), nullable=False, default="YYYY-MM-DD"
    )
    number_format: Mapped[str] = mapped_column(
        String(50), nullable=False, default="#,###.##"
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    session_timeout_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    default_theme: Mapped[str] = mapped_column(
        String(50), nullable=False, default="light"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
