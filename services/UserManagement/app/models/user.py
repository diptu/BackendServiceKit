"""User ORM model — platform identity, no credentials.

Authentication Service (a separate, later, not-yet-built service per
Implementation-order.md) owns passwords/MFA/sessions — this model only
ever carries profile/identity data, the same boundary IAM's own
UserProjection docstring already enforces on itself.
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
            "status IN ('pending','active','suspended','deactivated')",
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

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )

    @property
    def display_name(self) -> str:
        """Matches IAM's UserProjection.display_name field exactly."""
        return f"{self.first_name} {self.last_name}"
