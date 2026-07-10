"""MfaChallenge ORM model — the short-lived server-side handle for a login
step-up.

When a user with MFA enabled passes the password check, login does NOT return
tokens; it issues one of these (a random opaque token, hashed at rest) and
returns the raw handle. The client then presents that handle plus a TOTP or
recovery code to `/auth/mfa/verify` to actually obtain a session. This keeps
the "password verified" state entirely server-side and single-use — the
handle is worthless without the second factor and expires in minutes.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class MfaChallenge(Base):
    __tablename__ = "mfa_challenges"
    __table_args__ = (Index("idx_mfa_challenges_tenant_user", "tenant_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
