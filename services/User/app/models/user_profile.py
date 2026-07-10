"""UserProfile ORM model — profile-card content beyond identity.

Deliberately does not store first_name/last_name — those live on User
directly (used for display_name, IAM's UserProjection, and the
identity.events exchange).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    bio: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    pronouns: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_name_override: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
