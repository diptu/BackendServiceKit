"""Repository for ProvisioningResource persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.provisioning_resource import ProvisioningResource
from app.repositories.base import BaseRepository


class ProvisioningResourceRepository(BaseRepository[ProvisioningResource]):

    async def create(self, resource: ProvisioningResource) -> ProvisioningResource:
        self._session.add(resource)
        await self._session.flush()
        await self._session.refresh(resource)
        return resource

    async def get_by_id(self, resource_id: UUID) -> ProvisioningResource | None:
        result = await self._session.execute(
            select(ProvisioningResource).where(ProvisioningResource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant_id(self, tenant_id: UUID) -> list[ProvisioningResource]:
        result = await self._session.execute(
            select(ProvisioningResource)
            .where(ProvisioningResource.tenant_id == tenant_id)
            .order_by(ProvisioningResource.created_at.asc())
        )
        return list(result.scalars().all())

    async def list_by_job_id(self, job_id: UUID) -> list[ProvisioningResource]:
        result = await self._session.execute(
            select(ProvisioningResource)
            .where(ProvisioningResource.job_id == job_id)
            .order_by(ProvisioningResource.created_at.asc())
        )
        return list(result.scalars().all())
