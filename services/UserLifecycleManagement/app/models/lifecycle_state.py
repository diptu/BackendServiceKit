"""LifecycleState ORM model — this service's own view of a user's extended
lifecycle status (locked, in addition to whatever UserManagement tracks).

Created lazily on first transition, not on user creation — this service
doesn't consume UserManagement's user.created event this pass (see
TODO.md's Deferred section).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class LifecycleState(TimestampMixin, Base):
    __tablename__ = "lifecycle_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','suspended','locked','deactivated')",
            name="ck_lifecycle_states_valid_status",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        comment="Owning user (projection — not a FK; UserManagement owns the real row).",
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False)

    locked_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locked_by: Mapped[UUID | None] = mapped_column(nullable=True)
