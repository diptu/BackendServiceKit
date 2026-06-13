"""
Permission model for Role-Based Access Control (RBAC).

A permission represents an action that can be performed on a resource.

Examples:
    users:create
    users:read
    users:update
    users:delete
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from app.models.role_permission import RolePermission
from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Permission(Base):
    """
    RBAC permission model.

    Attributes:
        id: Unique permission identifier.
        name: Human-readable name.
        slug: Unique machine-readable permission key (e.g. "users:create").
        resource: Resource name (e.g. "users").
        action: Action name (e.g. "create").
        description: Human-readable description.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        roles: Roles assigned to this permission.
    """

    __tablename__ = "permissions"

    __table_args__ = (
        Index("idx_permissions_name", "name"),
        Index("idx_permissions_slug", "slug"),
        Index("idx_permissions_resource", "resource"),
        Index("idx_permissions_action", "action"),
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

    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
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

    # -------------------------------------------------------------
    # RBAC Relationships
    # -------------------------------------------------------------
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=RolePermission.__table__,
        back_populates="permissions",
        # Explicitly declare the bridge join vectors to prevent ambiguous key compilation
        foreign_keys=[RolePermission.role_id, RolePermission.permission_id],
    )

    def __repr__(self) -> str:
        """
        Return string representation of permission.

        Returns:
            str: Permission representation.
        """
        return (
            f"Permission("
            f"id={self.id}, "
            f"slug='{self.slug}', "
            f"resource='{self.resource}', "
            f"action='{self.action}'"
            f")"
        )