"""TenantLifecycleEvent ORM model — append-only audit log of all transitions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TenantLifecycleEvent(Base):
    """Immutable record of a single tenant lifecycle transition."""

    __tablename__ = "tenant_lifecycle_events"
    __table_args__ = (
        Index("idx_lifecycle_events_tenant_occurred", "tenant_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
    )

    from_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    transition: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    performed_by: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="api",
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
