"""
User model for authentication and authorization.

Represents a platform user that can be assigned roles via RBAC.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Explicitly import the association model class to hook into its table object
from app.models.user_role import UserRole

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.UserProfile.user_profile import UserProfile

# -------------------------------------------------------------
# Stateful Token Tracking Matrix (Simulated Cache/Store)
# -------------------------------------------------------------
# Maps refresh_jti -> token state metadata
ACTIVE_REFRESH_TOKENS: Dict[str, Dict[str, Any]] = {}


class User(Base):
    __tablename__ = "users"

    __table_args__ = (Index("idx_users_email", "email"),)

    # -------------------------
    # Identity (IAM CORE ONLY)
    # -------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # -------------------------
    # Account status (IAM CORE)
    # -------------------------
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------
    # timestamps
    # -------------------------
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

    # -------------------------
    # RBAC RELATIONSHIP
    # -------------------------
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role",
        secondary=UserRole.__table__,
        back_populates="users",
        # Explicitly declare tracking keys here to satisfy the User-side JoinCondition compiler
        foreign_keys=[UserRole.user_id, UserRole.role_id],
        lazy="selectin",
    )

    # -------------------------
    # PROFILE RELATIONSHIP (NEW)
    # -------------------------
    profile: Mapped["UserProfile"] = relationship(  # noqa: F821
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email})"

    @property
    def full_name(self) -> str | None:
        """
        Optional fallback (prefer profile.full_name later).
        """
        if self.profile:
            return self.profile.full_name
        return None
