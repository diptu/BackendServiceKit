# models/resource.py
"""
Resource model for IAM system.

A resource represents any protected entity in the system
that can be accessed via policies and permissions.

Examples:
    - users
    - payments
    - invoices
    - documents
    - projects
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Resource(Base):
    """
    IAM Resource model.

    A resource is a logical or physical entity that can be secured.

    Used by:
        - permissions (resource:action)
        - policies (resource-level rules)
        - policy engine evaluation
    """

    __tablename__ = "resources"

    __table_args__ = (
        Index("idx_resources_name", "name"),
        Index("idx_resources_type", "type"),
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
        String(100),
        unique=True,
        nullable=False,
    )

    # Example: "system", "domain", "api", "tenant"
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -------------------------
    # Schema / metadata for ABAC
    # -------------------------
    schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Example:
    # {
    #   "fields": ["owner_id", "tenant_id", "created_at"],
    #   "sensitive": ["ssn", "password"]
    # }

    # -------------------------
    # Access control hints
    # -------------------------
    is_public: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    # -------------------------
    # Lifecycle
    # -------------------------
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
        return f"Resource(id={self.id}, name='{self.name}', type='{self.type}')"
