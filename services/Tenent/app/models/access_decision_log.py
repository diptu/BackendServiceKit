"""AccessDecisionLog ORM model — audit trail for allow/deny decisions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AccessDecisionLog(Base):
    __tablename__ = "access_decision_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    caller_tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    target_tenant_id: Mapped[UUID | None] = mapped_column(nullable=True)
    resource_id: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_access_decision_logs_caller_tenant", "caller_tenant_id"),
        Index("idx_access_decision_logs_decided_at", "decided_at"),
        Index("idx_access_decision_logs_decision", "decision"),
    )
