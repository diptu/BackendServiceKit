"""
Role model for Role-Based Access Control (RBAC).

A role is a collection of permissions that can be assigned
to users.

Examples:
    super_admin
    organization_admin
    manager
    employee
    viewer
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(Base):
    """
    RBAC role model.

    Attributes:
        id: Unique role identifier.
        name: Human-readable role name.
        slug: Unique machine-readable role key.
        description: Role description.
        is_system: Indicates whether the role is system-managed.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        users: Users assigned to this role.
        permissions: Permissions assigned to this role.
    """

    __tablename__ = "roles"

    __table_args__ = (
        Index("idx_roles_name", "name"),
        Index("idx_roles_slug", "slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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

    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """
        Return string representation of role.

        Returns:
            str: Role representation.
        """
        return (
            f"Role("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"slug='{self.slug}'"
            f")"
        )