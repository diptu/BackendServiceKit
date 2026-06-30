"""TenantSettingsService — thin wrapper for settings CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.commands import UpdateTenantSettingsCmd
from app.models.tenant_settings import TenantSettings
from app.repositories.tenant_settings import TenantSettingsRepository


class TenantSettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._settings_repo = TenantSettingsRepository(session)

    async def get(self, tenant_id: uuid.UUID) -> TenantSettings | None:
        return await self._settings_repo.get_by_tenant_id(tenant_id)

    async def update(
        self, tenant_id: uuid.UUID, cmd: UpdateTenantSettingsCmd
    ) -> TenantSettings:
        settings = await self._settings_repo.get_by_tenant_id(tenant_id)
        if settings is None:
            settings = TenantSettings(id=uuid.uuid4(), tenant_id=tenant_id)

        for field_name, value in vars(cmd).items():
            if value is not None:
                setattr(settings, field_name, value)

        return await self._settings_repo.save(settings)
