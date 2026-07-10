"""ProvisioningJob ORM model — one physical-provisioning workflow per tenant.

This is a **global** table (one row per tenant across the whole platform) — the
provisioning orchestrator is what *creates* the per-tenant databases, so it
cannot itself be database-per-tenant. It records the workflow's status, the
current step, the created database name, and any failure, so a run is
resumable/retryable.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ProvisioningStatus
from app.infrastructure.database.base import Base, TimestampMixin


class ProvisioningJob(TimestampMixin, Base):
    __tablename__ = "provisioning_jobs"
    __table_args__ = (Index("idx_provisioning_jobs_status", "status"),)

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    subdomain: Mapped[str] = mapped_column(String(63), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProvisioningStatus.PENDING.value
    )
    current_step: Mapped[str | None] = mapped_column(String(40), nullable=True)
    db_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
