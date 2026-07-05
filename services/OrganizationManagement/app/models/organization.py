"""Organization ORM model — top-level business entity owned by a tenant."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Organization(TimestampMixin, Base):
    """Root container a tenant owns for workspaces/teams/groups/members/resources."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','deleted')",
            name="ck_organizations_valid_status",
        ),
        Index("idx_organizations_tenant_slug", "tenant_id", "slug", unique=True),
        Index("idx_organizations_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable organization name, e.g. 'Acme Corporation'.",
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="URL-safe identifier, unique within the tenant.",
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        comment="active while operating; deleted is terminal (soft-delete).",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )
