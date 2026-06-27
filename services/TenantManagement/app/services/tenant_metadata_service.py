"""TenantMetadataService — business logic for tenant key-value metadata."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TenantStatus
from app.domain.exceptions import TenantLockedError, TenantNotFoundError
from app.models.tenant_metadata import TenantMetadata
from app.repositories.tenant import TenantRepository
from app.repositories.tenant_metadata import TenantMetadataRepository
from app.schemas.tenant import UpdateTenantMetadataRequest

logger = logging.getLogger(__name__)


class TenantMetadataService:
    """Retrieves and upserts the key-value metadata attached to a tenant."""

    __slots__ = ("_tenant_repo", "_metadata_repo")

    def __init__(self, session: AsyncSession) -> None:
        self._tenant_repo = TenantRepository(session)
        self._metadata_repo = TenantMetadataRepository(session)

    async def get_metadata(self, tenant_id: UUID) -> list[TenantMetadata]:
        if not await self._tenant_repo.exists_by_id(tenant_id):
            raise TenantNotFoundError(tenant_id)
        return await self._metadata_repo.get_all_for_tenant(tenant_id)

    async def update_metadata(
        self, tenant_id: UUID, request: UpdateTenantMetadataRequest
    ) -> list[TenantMetadata]:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        if TenantStatus(tenant.status) == TenantStatus.ARCHIVED:
            raise TenantLockedError(tenant_id)

        await self._metadata_repo.upsert_many(tenant_id, request.metadata)
        return await self._metadata_repo.get_all_for_tenant(tenant_id)
