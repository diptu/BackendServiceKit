"""AuthEvent ORM model — append-only audit log of authentication activity.

`seq` (not `id`) is the real primary key, same reasoning as User's
UserStatusHistory: a plain auto-incrementing integer is the only reliable
"most recent first" ordering across SQLite (second-resolution timestamps)
and Postgres. `detail` must never contain a password, token, or OTP —
enforced by convention at the call site (services/auth_service.py), not by
the schema, since the column is a general-purpose free-text field.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AuthEvent(Base):
    __tablename__ = "auth_events"
    __table_args__ = (
        Index(
            "idx_auth_events_tenant_user_occurred",
            "tenant_id",
            "user_id",
            "occurred_at",
        ),
    )

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(unique=True, nullable=False)

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(nullable=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
