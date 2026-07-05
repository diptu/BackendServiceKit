"""UserStatusHistory ORM model — append-only audit log of status transitions.

Mirrors services/Tenent/app/models/lifecycle_event.py's shape exactly —
that table was designed for precisely this (an entity's lifecycle
transitions), a closer fit than a generic event log.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class UserStatusHistory(Base):
    """Immutable record of a single user status transition."""

    __tablename__ = "user_status_history"
    __table_args__ = (
        Index("idx_user_status_history_user_occurred", "user_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    performed_by: Mapped[UUID | None] = mapped_column(nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
