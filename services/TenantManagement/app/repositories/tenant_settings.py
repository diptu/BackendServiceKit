"""TenantSettingsRepository — CRUD for per-tenant configuration."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.tenant_settings import TenantSettings
from app.repositories.base import BaseRepository


class TenantSettingsRepository(BaseRepository[TenantSettings]):
    """Database operations for the TenantSettings entity (one row per tenant)."""

    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantSettings | None:
        """Return the settings record for the given tenant, or ``None``."""
        result = await self._session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create(self, settings: TenantSettings) -> TenantSettings:
        """Persist a new settings record and return it with server defaults."""
        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(settings)
        return settings

    async def save(self, settings: TenantSettings) -> TenantSettings:
        """Flush in-memory changes to a tracked settings record."""
        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(settings)
        return settings
