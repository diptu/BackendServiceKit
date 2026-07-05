"""OrganizationInvitation ORM model — secure, single-use invitation tokens.

Only `token_hash` (SHA-256 of a `secrets.token_urlsafe(32)` raw token) is
ever persisted — the raw token is returned once in the create-invitation
response and never stored, so a database read can't leak a usable token.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class OrganizationInvitation(TimestampMixin, Base):
    """A pending, accepted, expired, or revoked invitation to join an organization."""

    __tablename__ = "organization_invitations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','expired','revoked')",
            name="ck_organization_invitations_valid_status",
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

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")

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
