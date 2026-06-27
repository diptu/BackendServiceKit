"""TenantContact ORM model — tenant ownership and contacts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TenantContact(Base):
    """Tracks users who are owners or admins of a tenant.

    user_id is a projection — no FK to the User Service.
    Every tenant must have at least one active (removed_at IS NULL) owner.
    """

    __tablename__ = "tenant_contacts"
    __table_args__ = (
        Index("idx_tenant_contacts_tenant_user", "tenant_id", "user_id", unique=True),
        Index("idx_tenant_contacts_active", "tenant_id", "removed_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owner user_id — projection, not a FK to User Service.",
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="owner",
        comment="owner | admin",
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when contact is removed. NULL means currently active.",
    )
