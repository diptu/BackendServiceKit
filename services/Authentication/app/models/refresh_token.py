"""RefreshToken ORM model — opaque, server-side-revocable session tokens.

Only a SHA-256 hash of the raw token is ever persisted, same pattern as
User's UserInvitation token — the raw value is returned once, at issuance,
and never stored or logged. `replaced_by` chains rotations so a reused
(already-rotated) refresh token can be detected and the whole chain revoked,
the standard mitigation for refresh-token replay.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("idx_refresh_tokens_tenant_user", "tenant_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by: Mapped[UUID | None] = mapped_column(nullable=True)
