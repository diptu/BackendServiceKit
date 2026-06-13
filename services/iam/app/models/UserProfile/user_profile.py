"""
User profile model (separated from IAM core).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.db.base import Base
from app.models.UserProfile.user_social_link import UserSocialLink
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    # Import the User model only for type checkers to avoid runtime import cycles.
    from app.models.user import User


class UserProfile(Base):
    __tablename__ = "user_profiles"

    # -------------------------
    # 1–1 relationship with User
    # -------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # -------------------------
    # RELATIONSHIP BACK TO USER
    # -------------------------
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    # -------------------------
    # SOCIAL LINKS (1–N)
    # -------------------------
    social_links: Mapped[list["UserSocialLink"]] = relationship(
        "UserSocialLink",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )