"""SsoState ORM model — CSRF/replay guard for an in-flight OIDC login.

`/sso/login` mints a random `state` and `nonce`, stores them here, and sends
the user to the IdP. `/sso/callback` looks the row up by `state` (rejecting
unknown/expired/already-consumed values, which is the OIDC defence against
authorization-response injection) and checks the `nonce` inside the returned
id_token. Single-use via `consumed_at`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class SsoState(Base):
    __tablename__ = "sso_states"
    __table_args__ = (Index("idx_sso_states_tenant", "tenant_id"),)

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(2048), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
