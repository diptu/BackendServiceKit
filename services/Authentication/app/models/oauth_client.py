"""OAuthClient ORM model — a registered relying application allowed to run
the authorization-code flow against this service.

A confidential client stores a SHA-256 hash of its secret (never the raw
secret); a public client (e.g. a SPA/mobile app) has no secret and is
required to use PKCE instead. `redirect_uris` is an exact-match allow-list —
the redirect_uri on every authorize/token request must be one of these
verbatim, per OAuth2.1's tightened redirect rules.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class OAuthClient(Base):
    __tablename__ = "oauth_clients"
    __table_args__ = (Index("idx_oauth_clients_tenant", "tenant_id"),)

    client_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    client_secret_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    redirect_uris: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    allowed_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
