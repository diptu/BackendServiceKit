"""TenantLifecycleEvent ORM model — append-only audit log of all transitions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TenantLifecycleEvent(Base):
    """Immutable record of a single tenant lifecycle transition.

    Never updated after insert. Supports history queries and audit trails.
    """

    __tablename__ = "tenant_lifecycle_events"
    __table_args__ = (
        Index("idx_lifecycle_events_tenant_occurred", "tenant_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        index=True,
        comment="Tenant this event belongs to.",
    )

    from_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Status before this transition. NULL for the initial activation.",
    )

    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Status after this transition.",
    )

    transition: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Named transition action (activate, suspend, lock, archive, delete).",
    )

    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Human-readable reason provided by the caller.",
    )

    performed_by: Mapped[UUID | None] = mapped_column(
        nullable=True,
        comment="UUID of the actor who triggered the transition. NULL for system events.",
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="api",
        comment="Originating source: 'api', 'event:subscription.expired', etc.",
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the transition occurred (UTC).",
    )
