"""
Organization membership model.

Maps a user into a tenant (`Organization`) with exactly one `Role` that
governs what they may do inside that organization. Independent of the
platform-wide `UserRole` table used for JWT claims.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.role import Role
    from app.models.user import User


class OrganizationMember(Base):
    """
    User-organization membership with a single org-scoped role.

    Attributes:
        id: Unique membership identifier.
        organization_id: The tenant this membership belongs to.
        user_id: The member.
        role_id: The role this member holds within the organization.
        invited_by: User who added this member.
        is_active: Soft-suspend flag (membership exists but is disabled).
        joined_at: When the membership was created.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "organization_members"

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),
        Index("idx_org_members_organization_id", "organization_id"),
        Index("idx_org_members_user_id", "user_id"),
        Index("idx_org_members_role_id", "role_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # RESTRICT: a role in active use by a membership cannot be deleted
        # out from under it — callers must reassign members first.
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )

    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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

    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="members",
        foreign_keys=[organization_id],
    )

    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    role: Mapped[Role] = relationship(
        "Role",
        foreign_keys=[role_id],
        lazy="selectin",
    )

    invited_by_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[invited_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"OrganizationMember(id={self.id}, "
            f"organization_id={self.organization_id}, user_id={self.user_id})"
        )
