"""ResourceClaim ORM model — asserts that a resource belongs to a tenant."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ResourceClaim(Base):
    __tablename__ = "resource_claims"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_service: Mapped[str] = mapped_column(String(200), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "resource_type", "resource_id", name="uq_resource_claims_type_id"
        ),
        Index("idx_resource_claims_tenant_id", "tenant_id"),
        Index("idx_resource_claims_type_id", "resource_type", "resource_id"),
    )
