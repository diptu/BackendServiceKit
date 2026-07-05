"""Group ORM model + the group<->user membership association table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Group(TimestampMixin, Base):
    """A named, tenant-scoped collection of users."""

    __tablename__ = "groups"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','deleted')", name="ck_groups_valid_status"
        ),
        Index("idx_groups_tenant_name", "tenant_id", "name", unique=True),
        Index("idx_groups_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        comment="active while usable; deleted is terminal (soft-delete).",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )


class GroupMembership(Base):
    """Association: which users belong to a group.

    user_id is a plain column, not a FK to user_projections — Users are
    eventually-consistent projection data (same reasoning as tenant_id), so a
    hard FK could break on a membership created just before a projection
    sync lands, and historical memberships should survive a user's
    projection row being deleted. group_id is a real FK since Group is
    fully owned and synchronously consistent within IAM.
    """

    __tablename__ = "group_memberships"

    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
