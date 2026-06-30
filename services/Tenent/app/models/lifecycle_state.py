"""TenantLifecycleState ORM model — current lifecycle status per tenant."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TenantLifecycleState(Base):
    """Current lifecycle state for a single tenant (one row per tenant)."""

    __tablename__ = "tenant_lifecycle_states"
    __table_args__ = (Index("idx_lifecycle_states_tenant_id", "tenant_id", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        unique=True,
        comment="External tenant identifier. Not a FK — projection pattern.",
    )

    current_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="provisioning",
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
