"""Credential ORM model — the only place a password hash exists in this
platform. IAM's UserProjection and User's own User model both explicitly
never store passwords/MFA secrets; this service is where that boundary
lands. user_id is a projection reference (not a FK — crosses the User
service's database boundary, same plain-column-not-FK convention this repo
uses whenever a reference crosses a service boundary)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class Credential(TimestampMixin, Base):
    """One row per user — the credential a login attempt is checked against."""

    __tablename__ = "credentials"
    __table_args__ = (
        Index("idx_credentials_tenant_email", "tenant_id", "email", unique=True),
    )

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_algorithm: Mapped[str] = mapped_column(
        String(20), nullable=False, default="argon2id"
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
