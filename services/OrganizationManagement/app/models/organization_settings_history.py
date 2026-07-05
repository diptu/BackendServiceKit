"""OrganizationSettingsHistory ORM model — append-only version history.

A full snapshot of OrganizationSettings' fields is written every time
update_settings runs, incrementing `version` per organization.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class OrganizationSettingsHistory(Base):
    """An immutable snapshot of an organization's settings at a point in time."""

    __tablename__ = "organization_settings_history"
    __table_args__ = (
        Index(
            "idx_org_settings_history_org_version",
            "organization_id",
            "version",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    changed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
