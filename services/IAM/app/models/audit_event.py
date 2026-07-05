"""AuditEvent ORM model — append-only log of authorization-changing operations.

Scoped to grant/revoke relationships (who has access to what): role
assignment, role<->permission linkage, group membership, tenant
membership, entitlement grants. Not generic CRUD on Role/Permission/Group
definitions themselves — creating a Role record isn't a decision about
who can access what until it's assigned to someone, and that assignment
is what gets audited.

`actor_id` is optional and unverified — no Authentication Service exists
yet in this repo (see Implementation-order.md priority 5), so there is no
way to cryptographically know who is calling. When a caller supplies
`performed_by` in the request body, it's recorded as a courtesy audit
trail entry, not a verified identity claim. This is a known, accepted
limitation until Authentication exists — closing it further is out of
scope for this service.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AuditEvent(Base):
    """Immutable record of a single authorization-changing operation."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("idx_audit_events_tenant_occurred", "tenant_id", "occurred_at"),
        Index("idx_audit_events_subject_occurred", "subject_user_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    subject_user_id: Mapped[UUID | None] = mapped_column(
        nullable=True, comment="The user whose access changed, if applicable."
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(nullable=True)

    actor_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
        comment="Caller-supplied, unverified — see module docstring.",
    )
    details: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
