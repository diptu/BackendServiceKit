"""OrganizationMembership ORM model — a user's membership within an organization."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class OrganizationMembership(TimestampMixin, Base):
    """A user's membership within an organization (owner/admin/member/guest)."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        Index(
            "idx_org_memberships_org_user", "organization_id", "user_id", unique=True
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )
    user_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Projection reference to a User — not a FK, eventually consistent.",
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    invited_by: Mapped[UUID | None] = mapped_column(nullable=True)
