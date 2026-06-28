"""TenantMetadata ORM model — extensible key-value metadata per tenant."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin


class TenantMetadata(TimestampMixin, Base):
    """Stores arbitrary key-value metadata for a tenant.

    Schema-free — new metadata fields require no migration.
    """

    __tablename__ = "tenant_metadata"
    __table_args__ = (
        Index("idx_tenant_metadata_tenant_key", "tenant_id", "key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(2000), nullable=False)
