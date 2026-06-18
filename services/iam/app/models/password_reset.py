from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_TOKEN_BYTES = 32   # 256-bit raw entropy → 64-char hex digest stored
_DEFAULT_TTL = 15   # minutes


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # SHA-256 digest of the raw token — raw value is never persisted
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # NULL until consumed — single-use enforcement
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    def generate(
        cls, user_id: uuid.UUID, *, ttl_minutes: int = _DEFAULT_TTL
    ) -> tuple[PasswordResetToken, str]:
        """
        Returns (model_instance, raw_token).
        Persist the model; transmit only the raw_token to the user.
        Negative ttl_minutes produces an already-expired token (useful in tests).
        """
        raw = secrets.token_urlsafe(_TOKEN_BYTES)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        instance = cls(
            token_hash=digest,
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        return instance, raw

    @property
    def is_valid(self) -> bool:
        """True iff unused and not yet expired."""
        if self.used_at is not None:
            return False
        exp = self.expires_at
        # SQLite returns naive datetimes from DateTime(timezone=True); normalise.
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        return datetime.now(UTC) < exp
