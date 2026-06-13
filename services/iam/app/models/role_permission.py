"""
Role-permission association model.

Represents a permission assignment to a role.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RolePermission(Base):
    """
    Role-permission assignment model.

    Attributes:
        id: Unique assignment identifier.
        role_id: Role receiving the permission.
        permission_id: Assigned permission.
        assigned_by: User that granted the permission.
        assigned_at: Assignment timestamp.
        expires_at: Optional expiration timestamp.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        role: Related role.
        permission: Related permission.
    """

    __tablename__ = "role_permissions"

    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permission",
        ),
        Index(
            "idx_role_permissions_role_id",
            "role_id",
        ),
        Index(
            "idx_role_permissions_permission_id",
            "permission_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    role: Mapped["Role"] = relationship(
        "Role",
        lazy="selectin",
    )

    permission: Mapped["Permission"] = relationship(
        "Permission",
        lazy="selectin",
    )

    assigned_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """
        Return string representation.

        Returns:
            str: Role-permission assignment representation.
        """
        return (
            f"RolePermission("
            f"id={self.id}, "
            f"role_id={self.role_id}, "
            f"permission_id={self.permission_id}"
            f")"
        )