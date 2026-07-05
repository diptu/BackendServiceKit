"""LifecycleEvent ORM model — append-only audit log of every named transition.

Same shape as UserManagement's own UserStatusHistory / Tenent's
TenantLifecycleEvent. `event_type` distinguishes verbs that cause the same
status transition (e.g. activate vs onboard both end in ACTIVE).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"
    __table_args__ = (
        Index("idx_lifecycle_events_user_occurred", "user_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    performed_by: Mapped[UUID | None] = mapped_column(nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
