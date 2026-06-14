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
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.rbac import RoleEnum
from app.db.base import Base
from app.models.role_permission import RolePermission

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User


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
        Index("idx_roles_is_system", "is_system"),
        Index("idx_roles_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # =====================================================
    # ROLE METADATA
    # =====================================================
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        default=RoleEnum.GUEST.value.replace("_", " ").title(),
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        default=RoleEnum.GUEST.value,
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

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
        doc="Soft disable flag.",
    )
    # =====================================================
    # AUDIT FIELDS
    # =====================================================
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

    # -------------------------
    # RBAC RELATIONSHIPS
    # -------------------------
    users: Mapped[list[User]] = relationship(
        "User",
        secondary="user_roles",  # Can use string or variable if registered
        back_populates="roles",
        foreign_keys="[UserRole.user_id, UserRole.role_id]",
        lazy="selectin",
    )

    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary=RolePermission.__table__,
        back_populates="roles",
        # Pass the exact column bindings to satisfy the JoinCondition compiler
        foreign_keys=[RolePermission.role_id, RolePermission.permission_id],
        lazy="selectin",
    )

    # =====================================================
    # HELPER PROPERTIES
    # =====================================================

    @property
    def permission_count(self) -> int:
        """Return total assigned permissions."""
        return len(self.permissions)

    @property
    def user_count(self) -> int:
        """Return total assigned users."""
        return len(self.users)

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self) -> str:
        return (
            f"Role("
            f"id={self.id}, "
            f"slug='{self.slug}', "
            f"is_system={self.is_system}, "
            f"is_active={self.is_active}"
            f")"
        )

    def __str__(self) -> str:
        return self.slug
