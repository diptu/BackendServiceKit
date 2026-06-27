"""TenantMetadataRepository — key-value metadata storage for tenants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.tenant_metadata import TenantMetadata
from app.repositories.base import BaseRepository


class TenantMetadataRepository(BaseRepository[TenantMetadata]):
    """Database operations for the TenantMetadata entity.

    Metadata is stored as one row per key per tenant. Upsert semantics
    are applied: existing keys are overwritten, new keys are inserted.
    No keys are deleted by this repository — the caller must delete
    explicitly if needed.
    """

    async def get_all_for_tenant(self, tenant_id: UUID) -> list[TenantMetadata]:
        """Return all metadata entries for a tenant, ordered by key."""
        result = await self._session.execute(
            select(TenantMetadata)
            .where(TenantMetadata.tenant_id == tenant_id)
            .order_by(TenantMetadata.key)
        )
        return list(result.scalars())

    async def get_by_key(self, tenant_id: UUID, key: str) -> TenantMetadata | None:
        """Return a single metadata entry by tenant + key, or ``None``."""
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
        """Upsert a dict of key-value pairs for the given tenant.

        - Existing keys are **overwritten**.
        - New keys are **inserted**.
        - Unmentioned keys are left unchanged.

        Returns the full list of upserted entries in key order.
        """
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
        """Delete a single metadata entry. Returns ``True`` if deleted."""
        entry = await self.get_by_key(tenant_id, key)
        if entry is None:
            return False
        await self._session.delete(entry)
        await self._session.flush()
        return True
