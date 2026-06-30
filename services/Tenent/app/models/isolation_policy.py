"""IsolationPolicy ORM model — per-tenant access control rules."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class IsolationPolicy(Base, TimestampMixin):
    __tablename__ = "isolation_policies"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False, default="strict")
    allow_cross_tenant_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowed_partner_tenant_ids: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("idx_isolation_policies_tenant_id", "tenant_id"),
        Index("idx_isolation_policies_tenant_active", "tenant_id", "is_active"),
    )
