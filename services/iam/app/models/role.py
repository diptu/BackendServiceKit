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

from app.db.base import Base
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


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

#     users: Mapped[list["User"]] = relationship(
#         "User",
#         secondary=UserRole.__table__,
#         back_populates="roles",
#         # Mirror the explicit tracking columns here as well
#         foreign_keys=[UserRole.user_id, UserRole.role_id],
#         lazy="selectin",
#     )
#     permissions: Mapped[list["User"]] = relationship(
#         "User",  # <-- ERROR: This should be "Permission"
#         secondary=RolePermission.__table__,
#         back_populates="roles",  # <-- ERROR: This should look for "roles" or "permissions" on the target model
#         foreign_keys=[RolePermission.assigned_by, RolePermission.permission_id], # <-- ERROR: Wrong bridge keys
#         lazy="selectin",
#   )
    # -------------------------
    # RBAC RELATIONSHIPS
    # -------------------------
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_roles",  # Can use string or variable if registered
        back_populates="roles",
        foreign_keys="[UserRole.user_id, UserRole.role_id]",
        lazy="selectin",
    )

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=RolePermission.__table__,
        back_populates="roles",
        # Pass the exact column bindings to satisfy the JoinCondition compiler
        foreign_keys=[RolePermission.role_id, RolePermission.permission_id],
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