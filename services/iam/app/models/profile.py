"""
User profile model.

Stores non-authentication user information.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base):
    """
    User profile model.

    Attributes:
        user_id: Associated user identifier.
        first_name: User first name.
        last_name: User last name.
        display_name: Public display name.
        avatar_url: Profile image URL.
        bio: User biography.
        job_title: User job title.
        company: User company.
        website_url: Personal or company website.
        social_links: User's social media links.
        timezone: Preferred timezone.
        locale: Preferred language and locale.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        user: Related user.
    """

    __tablename__ = "user_profiles"

    __table_args__ = (
        Index(
            "idx_user_profiles_display_name",
            "display_name",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    website_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    social_links: Mapped[dict[str, str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    timezone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    locale: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

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

    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="profile",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """
        Return user's full name.

        Returns:
            str: Combined first and last name.
        """
        return (f"{self.first_name or ''} {self.last_name or ''}").strip()

    def __repr__(self) -> str:
        """
        Return string representation.

        Returns:
            str: User profile representation.
        """
        return (
            f"UserProfile(user_id={self.user_id}, display_name='{self.display_name}')"
        )
