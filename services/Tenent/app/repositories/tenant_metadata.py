"""TenantMetadataRepository — key-value metadata storage for tenants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.tenant_metadata import TenantMetadata
from app.repositories.base import BaseRepository


class TenantMetadataRepository(BaseRepository[TenantMetadata]):

    async def get_all_for_tenant(self, tenant_id: UUID) -> list[TenantMetadata]:
        result = await self._session.execute(
            select(TenantMetadata)
            .where(TenantMetadata.tenant_id == tenant_id)
            .order_by(TenantMetadata.key)
        )
        return list(result.scalars())

    async def get_by_key(self, tenant_id: UUID, key: str) -> TenantMetadata | None:
        result = await self._session.execute(
            select(TenantMetadata)
            .where(TenantMetadata.tenant_id == tenant_id)
            .where(TenantMetadata.key == key)
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        tenant_id: UUID,
        kv: dict[str, str],
    ) -> list[TenantMetadata]:
        from uuid import uuid4

        upserted: list[TenantMetadata] = []
        for key, value in kv.items():
            existing = await self.get_by_key(tenant_id, key)
            if existing is not None:
                existing.value = value
                self._session.add(existing)
                await self._session.flush()
                upserted.append(existing)
            else:
                entry = TenantMetadata(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    key=key,
                    value=value,
                )
                self._session.add(entry)
                await self._session.flush()
                await self._session.refresh(entry)
                upserted.append(entry)

        return sorted(upserted, key=lambda e: e.key)

    async def delete_by_key(self, tenant_id: UUID, key: str) -> bool:
        entry = await self.get_by_key(tenant_id, key)
        if entry is None:
            return False
        await self._session.delete(entry)
        await self._session.flush()
        return True
