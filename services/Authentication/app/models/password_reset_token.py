"""PasswordResetToken ORM model — single-use, hashed-at-rest reset tokens.

Same secure-token pattern as RefreshToken/User's invitation tokens: only a
SHA-256 hash is persisted, the raw token is returned once (in a real
deployment, emailed via NotificationService — not built in this repo yet,
see TODO.md) and never logged.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("idx_password_reset_tokens_user", "user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
