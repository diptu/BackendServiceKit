"""OrganizationSettings ORM model — per-organization configuration.

Uses the dialect-generic `sqlalchemy.JSON` type (not `postgresql.JSONB`) so
`feature_flags`/`compliance_rules` work identically against Postgres in
production and SQLite in tests — the same JSONB/SQLite trap this project's
IAM service already hit once (see its models/__init__.py comment) is avoided
here by construction rather than by a workaround.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class OrganizationSettings(Base):
    """Stores organization-scoped configuration (one row per organization)."""

    __tablename__ = "organization_settings"

    id: Mapped[UUID] = mapped_column(primary_key=True)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="en-US")
    default_member_role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="member"
    )
    feature_flags: Mapped[dict[str, bool]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    compliance_rules: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
