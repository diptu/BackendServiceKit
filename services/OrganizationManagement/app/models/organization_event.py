"""OrganizationEvent ORM model — append-only audit log of organization mutations.

Mirrors services/Tenent/app/models/lifecycle_event.py's shape exactly.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class OrganizationEvent(Base):
    """Immutable record of a single organization domain event."""

    __tablename__ = "organization_events"
    __table_args__ = (
        Index("idx_organization_events_org_occurred", "organization_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    organization_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    performed_by: Mapped[UUID | None] = mapped_column(nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
