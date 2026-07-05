"""UserPreferences ORM model — locale, timezone, and freeform extras."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class UserPreferences(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        comment="Owning user (projection — not a FK; UserManagement owns the real row).",
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    locale: Mapped[str] = mapped_column(String(35), nullable=False, default="en")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
