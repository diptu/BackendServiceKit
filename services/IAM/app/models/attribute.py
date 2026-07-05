"""Attribute ORM model — ABAC key/value data attached to a user."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Attribute(Base):
    """A single ABAC attribute (key/value pair) attached to a user.

    Hard-deleted on removal (unlike Role/Permission/Group/Entitlement) —
    key-value data, not an audited business entity.
    """

    __tablename__ = "attributes"
    __table_args__ = (
        Index(
            "idx_attributes_tenant_user_key", "tenant_id", "user_id", "key", unique=True
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
    value: Mapped[object] = mapped_column(JSON, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
