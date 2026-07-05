"""AccessReview ORM model — a record of an access-governance review."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class AccessReview(TimestampMixin, Base):
    """A review of a subject user's access to a resource, tracked to a decision."""

    __tablename__ = "access_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','revoked')",
            name="ck_access_reviews_valid_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )
    subject_user_id: Mapped[UUID] = mapped_column(
        nullable=False, comment="The user whose access is under review."
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        nullable=True, comment="The user performing the review; NULL until assigned."
    )

    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    decision_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
