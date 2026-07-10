"""MfaSecret ORM model — one TOTP shared secret per (tenant, user).

This is a second place, alongside `credentials.password_hash`, where a
recoverable authentication secret lives — and per this platform's boundary
(IAM's UserProjection and the User service both explicitly never store MFA
secrets) it belongs here in Authentication, nowhere else. Unlike a password,
a TOTP secret *cannot* be one-way hashed — verifying a code requires the
original secret — so it is stored recoverably; a production deployment must
encrypt this column at rest with a KMS-managed key (flagged in TODO.md).

`confirmed` gates activation: setup writes an unconfirmed row, and MFA only
takes effect on the account once the user proves possession with a valid
code (see MfaService.activate).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class MfaSecret(Base):
    __tablename__ = "mfa_secrets"

    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(primary_key=True)

    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
