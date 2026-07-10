"""AbacPolicy ORM model — a tenant-scoped attribute-based access rule.

`conditions` stores a small rule tree evaluated against a merged subject +
resource attribute context — see PolicyEvaluationService for the evaluator
and the precedence rules (priority order, deny-before-allow at a tie,
RBAC fallback, default-deny).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class AbacPolicy(TimestampMixin, Base):
    """A named, tenant-scoped ABAC rule: effect for resource_type+action if conditions match."""

    __tablename__ = "abac_policies"
    __table_args__ = (
        CheckConstraint(
            "effect IN ('allow','deny')", name="ck_abac_policies_valid_effect"
        ),
        Index("idx_abac_policies_tenant_name", "tenant_id", "name", unique=True),
        Index(
            "idx_abac_policies_tenant_resource_action",
            "tenant_id",
            "resource_type",
            "action",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="Owning tenant (projection — not a FK to Tenent's database).",
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    effect: Mapped[str] = mapped_column(String(10), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    priority: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set on soft-delete; NULL means not deleted.",
    )
