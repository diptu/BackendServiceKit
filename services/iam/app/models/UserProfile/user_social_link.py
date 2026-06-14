# app/models/user_social_link.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.UserProfile.user_profile import UserProfile


# Inside your UserSocialLink model file:


class UserSocialLink(Base):
    __tablename__ = "user_social_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # CRITICAL MATCH FIX: Reference 'user_profiles.user_id' because 'user_profiles.id' does not exist!
    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'github'
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile", back_populates="social_links"
    )
