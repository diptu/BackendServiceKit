"""Session ORM model — an authenticated user session within a tenant.

This is the platform's higher-level session/device tracking (concurrent
sessions, force-logout, "where am I logged in"), distinct from Authentication's
own refresh-token rotation. Like every other secure token in the platform,
only a SHA-256 hash of the opaque session token is persisted; the raw token is
returned once at creation and never stored or logged.

`user_id` is a projection reference (a plain column, not an FK) — it names an
identity the User service owns, following the repo's cross-service convention.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("idx_sessions_tenant_user", "tenant_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
