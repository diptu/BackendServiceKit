"""OrganizationSettingsRepository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.organization_settings import OrganizationSettings
from app.repositories.base import BaseRepository


class OrganizationSettingsRepository(BaseRepository[OrganizationSettings]):
    async def create(self, settings: OrganizationSettings) -> OrganizationSettings:
        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(settings)
        return settings

    async def save(self, settings: OrganizationSettings) -> OrganizationSettings:
        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(settings)
        return settings

    async def get_by_organization_id(
        self, organization_id: UUID
    ) -> OrganizationSettings | None:
        result = await self._session.execute(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()
