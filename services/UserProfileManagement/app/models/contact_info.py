"""ContactInfo ORM model — contact details beyond UserManagement's primary email."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class ContactInfo(TimestampMixin, Base):
    __tablename__ = "contact_info"

    user_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        comment="Owning user (projection — not a FK; UserManagement owns the real row).",
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
