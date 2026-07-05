"""Avatar ORM model — stores a URL reference, not raw image bytes.

No blob storage service exists anywhere in this repo yet — the client is
expected to have already uploaded the image elsewhere (CDN/object store)
and hands this service the resulting URL.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Avatar(Base):
    __tablename__ = "avatars"

    user_id: Mapped[UUID] = mapped_column(
        primary_key=True,
        comment="Owning user (projection — not a FK; UserManagement owns the real row).",
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
