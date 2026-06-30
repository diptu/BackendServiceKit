"""ProvisioningResource ORM model — tracks each infrastructure resource created."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ProvisioningResource(Base):
    __tablename__ = "provisioning_resources"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("provisioning_jobs.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="provisioned"
    )
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    provisioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_provisioning_resources_tenant_id", "tenant_id"),
        Index("idx_provisioning_resources_job_id", "job_id"),
        Index("idx_provisioning_resources_tenant_type", "tenant_id", "resource_type"),
    )
