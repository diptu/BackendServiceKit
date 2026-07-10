"""AuthorizationCode ORM model — the single-use code handed back from
`/oauth/authorize` and redeemed once at `/oauth/token`.

Only a SHA-256 hash of the code is stored. The row binds the code to the
client, the resource owner (user), the exact redirect_uri, the granted
scopes, and the PKCE challenge — every one of those is re-checked at
redemption, and `consumed_at` makes redemption single-use (a second
presentation is rejected as replay).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class AuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"
    __table_args__ = (Index("idx_oauth_auth_codes_tenant", "tenant_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    redirect_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    code_challenge: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_challenge_method: Mapped[str | None] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
