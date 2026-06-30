"""ResourceClaimService — manages resource ownership claims."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import CACHE_TTL_CLAIM
from app.domain.events import ResourceClaimed, ResourceClaimReleased
from app.domain.exceptions import ResourceClaimNotFoundError
from app.events.isolation_events import EventPublisher, publish_event
from app.infrastructure.cache.redis_cache import cache_delete, cache_set_str, claim_cache_key
from app.infrastructure.messaging.publisher import NullPublisher
from app.models.resource_claim import ResourceClaim
from app.repositories.resource_claim import ResourceClaimRepository
from app.schemas.isolation import ClaimItem

logger = logging.getLogger(__name__)


class ResourceClaimService:
    __slots__ = ("_claim_repo", "_publisher")

    def __init__(self, session: AsyncSession, publisher: Any = None) -> None:
        self._claim_repo = ResourceClaimRepository(session)
        self._publisher: EventPublisher = publisher or NullPublisher()

    async def claim(
        self,
        tenant_id: UUID,
        resource_id: str,
        resource_type: str,
        source_service: str,
    ) -> ResourceClaim:
        claim = await self._claim_repo.claim(
            tenant_id, resource_id, resource_type, source_service
        )

        await cache_set_str(
            claim_cache_key(resource_type, resource_id),
            str(tenant_id),
            ttl=CACHE_TTL_CLAIM,
        )

        await publish_event(
            ResourceClaimed(
                tenant_id=tenant_id,
                resource_id=resource_id,
                resource_type=resource_type,
                source_service=source_service,
            ),
            self._publisher,
        )

        return claim

    async def release(
        self, tenant_id: UUID, resource_id: str, resource_type: str
    ) -> None:
        await self._claim_repo.release(tenant_id, resource_id, resource_type)

        await cache_delete(claim_cache_key(resource_type, resource_id))

        await publish_event(
            ResourceClaimReleased(
                tenant_id=tenant_id,
                resource_id=resource_id,
                resource_type=resource_type,
            ),
            self._publisher,
        )

    async def get_owner(self, resource_id: str, resource_type: str) -> ResourceClaim:
        claim = await self._claim_repo.get_owner(resource_id, resource_type)
        if claim is None:
            raise ResourceClaimNotFoundError(resource_id, resource_type)
        return claim

    async def bulk_claim(
        self,
        tenant_id: UUID,
        claims: list[ClaimItem],
        source_service: str,
    ) -> list[ResourceClaim]:
        results: list[ResourceClaim] = []
        for item in claims:
            result = await self.claim(
                tenant_id, item.resource_id, str(item.resource_type), source_service
            )
            results.append(result)
        return results
