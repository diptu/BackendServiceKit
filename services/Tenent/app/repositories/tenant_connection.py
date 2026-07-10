"""TenantConnectionRepository — CRUD for the Control Plane registry.

No tenant_id scoping keyword here (unlike the isolation/policy repositories):
the Control Plane is the one global table that spans all tenants by design —
its whole job is to answer "given any tenant/subdomain, where does it live."
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.tenant_connection import TenantConnection
from app.repositories.base import BaseRepository


class TenantConnectionRepository(BaseRepository[TenantConnection]):
    async def upsert(self, connection: TenantConnection) -> TenantConnection:
        merged = await self._session.merge(connection)
        await self._session.flush()
        # Refresh within the async context so server-managed columns
        # (created_at/updated_at) are materialized and not lazy-loaded later.
        await self._session.refresh(merged)
        return merged

    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantConnection | None:
        result = await self._session.execute(
            select(TenantConnection).where(TenantConnection.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_subdomain(self, subdomain: str) -> TenantConnection | None:
        result = await self._session.execute(
            select(TenantConnection).where(TenantConnection.subdomain == subdomain)
        )
        return result.scalar_one_or_none()

    async def save(self, connection: TenantConnection) -> TenantConnection:
        self._session.add(connection)
        await self._session.flush()
        await self._session.refresh(connection)
        return connection
