"""ContactInfo ORM model — contact details beyond the primary email on User."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class ContactInfo(TimestampMixin, Base):
    __tablename__ = "contact_info"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
