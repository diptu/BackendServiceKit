"""UserStatusHistory ORM model — append-only audit log of status transitions.

Merges UserManagement's own UserStatusHistory with
UserLifecycleManagement's LifecycleEvent — now that both are the same
table (one status, one service), `action` carries the verb distinction
(activate vs onboard, deactivate vs offboard) that LifecycleEvent's
`event_type` used to.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class UserStatusHistory(Base):
    """Immutable record of a single user status transition.

    `seq` (not `id`) is the real primary key — a plain auto-incrementing
    integer, portable across SQLite and Postgres, used purely for reliable
    ordering. `occurred_at` alone isn't reliable for "most recent first"
    ordering: SQLite's `now()` is only second-resolution, so two
    transitions in the same test (or the same busy second in production)
    can land on an identical timestamp. `id` stays as a separate unique
    UUID for external reference — API responses expose `id`, not `seq`.
    """

    __tablename__ = "user_status_history"
    __table_args__ = (
        Index("idx_user_status_history_user_occurred", "user_id", "occurred_at"),
    )

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(unique=True, nullable=False)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    performed_by: Mapped[UUID | None] = mapped_column(nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
