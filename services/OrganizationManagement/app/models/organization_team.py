"""OrganizationTeam ORM model + the team<->user membership association table.

A single table backs both "teams" and "departments" (`team_type` column) —
per the plan, these are the same shape (name, description, optional
parent for hierarchy), just a different label; two near-identical tables
would be unearned duplication.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class OrganizationTeam(TimestampMixin, Base):
    """A team or department within an organization, optionally nested."""

    __tablename__ = "organization_teams"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','deleted')", name="ck_organization_teams_valid_status"
        ),
        CheckConstraint(
            "team_type IN ('team','department')",
            name="ck_organization_teams_valid_type",
        ),
        Index(
            "idx_organization_teams_org_name", "organization_id", "name", unique=True
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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    team_type: Mapped[str] = mapped_column(String(20), nullable=False, default="team")

    parent_team_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organization_teams.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )


class TeamMembership(Base):
    """Association: which users belong to a team.

    user_id is a plain column, not a FK — same eventually-consistent
    projection reasoning as OrganizationMembership.user_id.
    """

    __tablename__ = "team_memberships"

    team_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization_teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
