"""ResourceClaimService — manage tenant resource ownership claims."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource_claim import ResourceClaim
from app.repositories.base import PageResult
from app.repositories.resource_claim import ResourceClaimRepository


class ResourceClaimService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ResourceClaimRepository(session)

    async def claim(
        self,
        tenant_id: uuid.UUID,
        resource_id: str,
        resource_type: str,
        source_service: str,
    ) -> ResourceClaim:
        return await self._repo.claim(
            tenant_id, resource_id, resource_type, source_service
        )

    async def bulk_claim(
        self,
        tenant_id: uuid.UUID,
        claims: list[dict[str, str]],
        source_service: str,
    ) -> list[ResourceClaim]:
        return await self._repo.bulk_claim(tenant_id, claims, source_service)

    async def release(
        self,
        tenant_id: uuid.UUID,
        resource_id: str,
        resource_type: str,
    ) -> None:
        return await self._repo.release(tenant_id, resource_id, resource_type)

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[ResourceClaim]:
        return await self._repo.list_by_tenant(
            tenant_id, next_cursor=cursor, limit=limit
        )
