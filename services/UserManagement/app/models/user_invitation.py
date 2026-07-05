"""UserInvitation ORM model — secure, single-use platform onboarding invitations.

Same shape as OrganizationManagement's OrganizationInvitation minus
organization_id/role (platform invitations don't attach to an org or grant
a role — that's OrganizationManagement's separate concern). Only
`token_hash` is ever persisted, never the raw token.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class UserInvitation(TimestampMixin, Base):
    """A pending, accepted, expired, or revoked platform invitation."""

    __tablename__ = "user_invitations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','expired','revoked')",
            name="ck_user_invitations_valid_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    invited_by: Mapped[UUID] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
