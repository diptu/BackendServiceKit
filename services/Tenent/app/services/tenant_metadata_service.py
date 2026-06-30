"""TenantMetadataService — key-value metadata management."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_metadata import TenantMetadata
from app.repositories.tenant_metadata import TenantMetadataRepository


class TenantMetadataService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = TenantMetadataRepository(session)

    async def get(self, tenant_id: uuid.UUID) -> list[TenantMetadata]:
        return await self._repo.get_all_for_tenant(tenant_id)

    async def update(
        self, tenant_id: uuid.UUID, kv: dict[str, str]
    ) -> list[TenantMetadata]:
        return await self._repo.upsert_many(tenant_id, kv)

    async def delete_key(self, tenant_id: uuid.UUID, key: str) -> bool:
        return await self._repo.delete_by_key(tenant_id, key)
