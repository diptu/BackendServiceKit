"""TenantSettingsService — business logic for per-tenant configuration."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TenantStatus
from app.domain.events import TenantConfigurationUpdated
from app.domain.exceptions import TenantLockedError, TenantNotFoundError
from app.models.tenant_settings import TenantSettings
from app.repositories.tenant import TenantRepository
from app.repositories.tenant_settings import TenantSettingsRepository
from app.schemas.tenant import UpdateTenantSettingsRequest

logger = logging.getLogger(__name__)

_SYSTEM_ACTOR = UUID("00000000-0000-0000-0000-000000000000")


def _emit(event: Any) -> None:
    logger.debug("domain_event", extra={"event_type": type(event).__name__, **asdict(event)})


class TenantSettingsService:
    """Retrieves and updates the single TenantSettings record per tenant."""

    __slots__ = ("_tenant_repo", "_settings_repo")

    def __init__(self, session: AsyncSession) -> None:
        self._tenant_repo = TenantRepository(session)
        self._settings_repo = TenantSettingsRepository(session)

    async def get(self, tenant_id: UUID) -> TenantSettings:
        if not await self._tenant_repo.exists_by_id(tenant_id):
            raise TenantNotFoundError(tenant_id)
        settings = await self._settings_repo.get_by_tenant_id(tenant_id)
        if settings is None:
            raise TenantNotFoundError(tenant_id)
        return settings

    async def update(
        self, tenant_id: UUID, request: UpdateTenantSettingsRequest
    ) -> TenantSettings:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        if TenantStatus(tenant.status) == TenantStatus.ARCHIVED:
            raise TenantLockedError(tenant_id)

        settings = await self._settings_repo.get_by_tenant_id(tenant_id)
        if settings is None:
            # Settings should always exist — create defaults if somehow missing.
            settings = TenantSettings(id=uuid4(), tenant_id=tenant_id)
            await self._settings_repo.create(settings)

        changed = False
        for field_name in (
            "timezone",
            "locale",
            "language",
            "date_format",
            "number_format",
            "currency",
            "session_timeout_minutes",
            "default_theme",
        ):
            new_val = getattr(request, field_name)
            if new_val is not None and getattr(settings, field_name) != new_val:
                setattr(settings, field_name, new_val)
                changed = True

        if changed:
            settings = await self._settings_repo.save(settings)
            _emit(TenantConfigurationUpdated(tenant_id=tenant_id, updated_by=_SYSTEM_ACTOR))

        return settings
