"""Entitlement ORM model — what a user is granted (as opposed to what they can do)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Entitlement(TimestampMixin, Base):
    """A grant of something a user is allowed to have (a seat, a quota, a feature)."""

    __tablename__ = "entitlements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','revoked')", name="ck_entitlements_valid_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )
    user_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Projection reference to user_projections.id — not a FK "
        "(eventually-consistent, see GroupMembership).",
    )

    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[object | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )
