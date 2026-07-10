"""MfaRecoveryCode ORM model — single-use backup codes for TOTP.

Only a SHA-256 hash of each code is persisted (same hashed-at-rest pattern as
refresh/reset tokens); the raw codes are shown once at enrollment and never
again. `used_at` enforces single use.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class MfaRecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"
    __table_args__ = (
        Index("idx_mfa_recovery_codes_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
