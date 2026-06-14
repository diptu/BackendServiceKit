# models/policy.py
"""
Policy model for IAM system.

A policy defines authorization rules evaluated by the policy engine.

Supports:
- RBAC-based rules
- ABAC conditions (future-ready)
- resource-action evaluation
- allow/deny effects
- versioning for safe updates
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Policy(Base):
    """
    IAM Policy model.

    A policy defines rules that control access decisions.

    Example:
        - Allow: users:read if role == admin
        - Deny: payment:delete if not superuser
    """

    __tablename__ = "policies"

    __table_args__ = (
        Index("idx_policies_name", "name"),
        Index("idx_policies_effect", "effect"),
        Index("idx_policies_resource", "resource"),
        Index("idx_policies_action", "action"),
    )

    # -------------------------
    # Identity
    # -------------------------
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

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -------------------------
    # Core policy definition
    # -------------------------
    effect: Mapped[str] = mapped_column(
        String(10),  # allow | deny
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

    # -------------------------
    # ABAC / advanced conditions
    # -------------------------
    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Example:
    # {
    #   "user.role": "admin",
    #   "request.ip": "10.0.0.0/8",
    #   "resource.owner_id": "user.id"
    # }

    # -------------------------
    # Metadata / lifecycle
    # -------------------------
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
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

    # -------------------------
    # Ownership / audit
    # -------------------------
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"Policy("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"effect='{self.effect}', "
            f"resource='{self.resource}', "
            f"action='{self.action}'"
            f")"
        )
