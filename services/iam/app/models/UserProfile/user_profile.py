"""
User profile model (separated from IAM core).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    # Use standard type checking guards for all relational targets to keep imports linear
    from app.models.user import User
    from app.models.UserProfile.user_social_link import UserSocialLink


class UserProfile(Base):
    """
    Extended profile metadata bound 1-to-1 with Core Identity Users.
    Uses a shared primary key strategy to guarantee relational constraint symmetry.
    """

    __tablename__ = "user_profiles"

    # -------------------------------------------------------------
    # Primary Identity / 1–1 mapping with User
    # -------------------------------------------------------------
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
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # -------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    social_links: Mapped[list["UserSocialLink"]] = relationship(
        "UserSocialLink",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"UserProfile(user_id={self.user_id}, full_name='{self.full_name}')"
