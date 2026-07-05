"""Role ORM model — a named, tenant-scoped bundle of permissions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Role(TimestampMixin, Base):
    """A named, tenant-scoped role that can be assigned to users."""

    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("status IN ('active','deleted')", name="ck_roles_valid_status"),
        Index("idx_roles_tenant_name", "tenant_id", "name", unique=True),
        Index("idx_roles_tenant_status", "tenant_id", "status"),
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
