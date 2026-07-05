"""Association tables for user<->role assignment and tenant membership."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class UserRole(Base):
    """Association: which roles are assigned to a user.

    user_id is a plain column, not a FK to user_projections — see
    GroupMembership's docstring for the eventual-consistency rationale.
    role_id is a real FK since Role is fully owned and synchronously
    consistent within IAM.
    """

    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Defense-in-depth scoping column; role_id already implies a "
        "tenant via roles.tenant_id.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TenantMembership(Base):
    """A user's membership within a tenant (distinct from group membership)."""

    __tablename__ = "tenant_memberships"

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(primary_key=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
