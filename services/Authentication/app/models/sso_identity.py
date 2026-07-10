"""SsoIdentity ORM model — the durable link between an external IdP subject
and a local user_id.

The first successful federated login is matched to a local credential by
email; from then on this row lets subsequent logins match on the stable IdP
`subject` claim instead (emails change, `sub` does not). `user_id` is a plain
column, not an FK — it references an identity the User service owns, same
cross-boundary convention as `credentials.user_id`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class SsoIdentity(Base):
    __tablename__ = "sso_identities"
    __table_args__ = (
        Index(
            "idx_sso_identities_lookup",
            "tenant_id",
            "provider",
            "subject",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
