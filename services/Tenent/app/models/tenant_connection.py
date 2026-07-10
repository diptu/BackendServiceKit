"""TenantConnection ORM model — the Control Plane registry row.

This is the authoritative "which physical database does tenant X live in, and
what subdomain routes to it" map that makes Siloed (database-per-tenant)
multi-tenancy possible. It is the one table every other service's connection
router ultimately reads from (via Tenent's Control Plane API), and the table
the gateway's Tenant Resolver consults to turn a subdomain into a tenant.

Two deliberate properties:

1. **It is global, not siloed.** A registry of all tenants' databases cannot
   itself be per-tenant — it lives in Tenent's own single Control Plane
   database. This is the one place in the platform that is intentionally NOT
   database-per-tenant.
2. **It never stores a raw password.** Only the connection *coordinates*
   (driver/host/port/name/user) plus a `secret_ref` — a lookup key resolved
   against a secrets backend at connect time (see app/infrastructure/secrets.py).
   Keeping credentials out of this table is what makes it safe to expose the
   non-secret parts to the gateway for subdomain resolution.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import TenantConnectionStatus
from app.infrastructure.database.base import Base, TimestampMixin


class TenantConnection(TimestampMixin, Base):
    __tablename__ = "tenant_connections"
    __table_args__ = (
        Index("idx_tenant_connections_subdomain", "subdomain", unique=True),
    )

    # One connection record per tenant. tenant_id is a projection reference
    # (the Tenant lives in this same service, but the record is keyed by the
    # tenant's id, mirroring the plain-column convention used elsewhere).
    tenant_id: Mapped[UUID] = mapped_column(primary_key=True)

    subdomain: Mapped[str] = mapped_column(String(63), nullable=False)

    db_driver: Mapped[str] = mapped_column(
        String(64), nullable=False, default="postgresql+asyncpg"
    )
    db_host: Mapped[str] = mapped_column(String(255), nullable=False)
    db_port: Mapped[int] = mapped_column(Integer, nullable=False, default=5432)
    db_name: Mapped[str] = mapped_column(String(255), nullable=False)
    db_user: Mapped[str] = mapped_column(String(255), nullable=False)

    # Reference to the password in a secrets backend — NOT the password itself.
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TenantConnectionStatus.PROVISIONING.value
    )
