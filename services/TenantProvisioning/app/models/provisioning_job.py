"""ProvisioningJob ORM model — tracks one provisioning attempt per tenant."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ProvisioningJob(Base):
    __tablename__ = "provisioning_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_steps: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_provisioning_jobs_tenant_id", "tenant_id"),
        Index("idx_provisioning_jobs_status", "status"),
        Index("idx_provisioning_jobs_tenant_created", "tenant_id", "created_at"),
    )
