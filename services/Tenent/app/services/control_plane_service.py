"""ControlPlaneService — the authoritative tenant → database registry.

This is Tenent's role in Siloed multi-tenancy: it owns the mapping every other
service's connection router and the gateway's subdomain resolver depend on.

- `resolve_subdomain` powers the gateway's Tenant Resolver (subdomain → tenant),
  and returns no credentials.
- `get_connection` returns the non-secret connection coordinates.
- `build_dsn` assembles a full connection string by resolving the stored
  `secret_ref` through the injected SecretsProvider — the only method that ever
  touches a credential, and it fails closed if the secret is missing.
- `register` / `deprovision` are driven by tenant provisioning/offboarding.
"""

from __future__ import annotations

import uuid
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TenantConnectionStatus
from app.domain.exceptions import (
    SubdomainConflictError,
    SubdomainNotFoundError,
    TenantConnectionNotFoundError,
)
from app.infrastructure.secrets import EnvSecretsProvider, SecretsProvider
from app.models.tenant_connection import TenantConnection
from app.repositories.tenant_connection import TenantConnectionRepository


class ControlPlaneService:
    def __init__(
        self, session: AsyncSession, secrets: SecretsProvider | None = None
    ) -> None:
        self._repo = TenantConnectionRepository(session)
        self._secrets = secrets or EnvSecretsProvider()

    async def register(
        self,
        tenant_id: uuid.UUID,
        *,
        subdomain: str,
        db_host: str,
        db_name: str,
        db_user: str,
        db_driver: str = "postgresql+asyncpg",
        db_port: int = 5432,
        secret_ref: str | None = None,
        region: str | None = None,
        status: TenantConnectionStatus = TenantConnectionStatus.PROVISIONING,
    ) -> TenantConnection:
        """Register or update a tenant's database home. Idempotent per tenant;
        rejects a subdomain already owned by a different tenant."""
        subdomain = subdomain.strip().lower()
        existing_by_subdomain = await self._repo.get_by_subdomain(subdomain)
        if existing_by_subdomain is not None and (
            existing_by_subdomain.tenant_id != tenant_id
        ):
            raise SubdomainConflictError(subdomain)

        return await self._repo.upsert(
            TenantConnection(
                tenant_id=tenant_id,
                subdomain=subdomain,
                db_driver=db_driver,
                db_host=db_host,
                db_port=db_port,
                db_name=db_name,
                db_user=db_user,
                secret_ref=secret_ref,
                region=region,
                status=status.value,
            )
        )

    async def get_connection(self, tenant_id: uuid.UUID) -> TenantConnection:
        connection = await self._repo.get_by_tenant_id(tenant_id)
        if connection is None:
            raise TenantConnectionNotFoundError(tenant_id)
        return connection

    async def resolve_subdomain(self, subdomain: str) -> TenantConnection:
        connection = await self._repo.get_by_subdomain(subdomain.strip().lower())
        if connection is None:
            raise SubdomainNotFoundError(subdomain)
        return connection

    async def build_dsn(self, tenant_id: uuid.UUID) -> str:
        """Assemble the full SQLAlchemy connection URL for a tenant, resolving
        the credential from the secrets backend. Fails closed
        (TenantSecretUnavailableError) if a referenced secret is missing."""
        conn = await self.get_connection(tenant_id)
        userinfo = quote_plus(conn.db_user)
        if conn.secret_ref:
            password = await self._secrets.get(conn.secret_ref)
            userinfo = f"{userinfo}:{quote_plus(password)}"
        return f"{conn.db_driver}://{userinfo}@{conn.db_host}:{conn.db_port}/{conn.db_name}"

    async def set_status(
        self, tenant_id: uuid.UUID, status: TenantConnectionStatus
    ) -> TenantConnection:
        conn = await self.get_connection(tenant_id)
        conn.status = status.value
        return await self._repo.save(conn)

    async def deprovision(self, tenant_id: uuid.UUID) -> None:
        """Mark a tenant's connection DISABLED so nothing routes to it after
        offboarding. The physical drop/archive of the database is a separate,
        deployment-specific step."""
        await self.set_status(tenant_id, TenantConnectionStatus.DISABLED)
