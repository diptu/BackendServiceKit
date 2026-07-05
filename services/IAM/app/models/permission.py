"""Permission ORM model + the role<->permission association table."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Permission(TimestampMixin, Base):
    """A named, tenant-scoped capability (convention: 'resource:action', e.g. 'users:read')."""

    __tablename__ = "permissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','deleted')", name="ck_permissions_valid_status"
        ),
        Index("idx_permissions_tenant_name", "tenant_id", "name", unique=True),
        Index("idx_permissions_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Convention: 'resource:action', e.g. 'users:read'.",
    )
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


class RolePermission(Base):
    """Association: which permissions a role grants.

    Real FKs on both sides — Role and Permission are both fully owned and
    synchronously consistent within IAM's own schema (unlike user_id
    references elsewhere, which stay plain columns; see GroupMembership).
    """

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
