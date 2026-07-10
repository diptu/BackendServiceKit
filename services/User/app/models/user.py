"""User ORM model — platform identity, status lifecycle, no credentials.

Authentication Service (a separate, later, not-yet-built service per
Implementation-order.md) owns passwords/MFA/sessions — this model only
ever carries profile/identity data.

locked_reason/locked_by were a separate LifecycleState table in
UserLifecycleManagement (needed because that was a different service —
"locked" had to be tracked locally there and proxied to this service as
"suspended"). Now that it's the same service and the same row, `locked`
is just a real value of `status`, and its reason/actor are plain nullable
columns here — no more proxy, no more separate table.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """A platform identity, scoped to a tenant."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','suspended','locked','deactivated')",
            name="ck_users_valid_status",
        ),
        Index("idx_users_tenant_email", "tenant_id", "email", unique=True),
        Index("idx_users_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    locked_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    locked_by: Mapped[UUID | None] = mapped_column(nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )

    @property
    def display_name(self) -> str:
        """Matches IAM's UserProjection.display_name field exactly."""
        return f"{self.first_name} {self.last_name}"
