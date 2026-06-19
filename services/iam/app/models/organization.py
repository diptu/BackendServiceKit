"""
Organization model — multi-tenancy boundary.

An organization is the tenant root: users join it via `OrganizationMember`
rows, each carrying exactly one `Role` (global system org-role or a custom
role scoped to this organization) that governs what they may do inside it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization_member import OrganizationMember
    from app.models.role import Role
    from app.models.user import User


class Organization(Base):
    """
    Tenant root entity.

    Attributes:
        id: Unique organization identifier.
        name: Human-readable organization name.
        slug: Unique machine-readable organization key (used in URLs).
        description: Optional description.
        owner_id: User who created/owns the organization.
        is_active: Soft disable flag.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        members: Membership rows (user + role) for this organization.
        roles: Custom roles scoped to this organization.
    """

    __tablename__ = "organizations"

    __table_args__ = (
        Index("idx_organizations_slug", "slug"),
        Index("idx_organizations_owner_id", "owner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped[User] = relationship(
        "User",
        foreign_keys=[owner_id],
        lazy="selectin",
    )

    members: Mapped[list[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    roles: Mapped[list[Role]] = relationship(
        "Role",
        back_populates="organization",
        lazy="selectin",
    )

    @property
    def member_count(self) -> int:
        """Return total members in this organization."""
        return len(self.members)

    def __repr__(self) -> str:
        return f"Organization(id={self.id}, slug='{self.slug}')"

    def __str__(self) -> str:
        return self.slug
