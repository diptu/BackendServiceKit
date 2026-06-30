"""Repository for ResourceClaim persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import ResourceClaimConflictError
from app.models.resource_claim import ResourceClaim
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class ResourceClaimRepository(BaseRepository[ResourceClaim]):
    async def claim(
        self,
        tenant_id: UUID,
        resource_id: str,
        resource_type: str,
        source_service: str,
    ) -> ResourceClaim:
        existing = await self.get_owner(resource_id, resource_type)
        if existing is not None:
            if existing.tenant_id == tenant_id:
                return existing
            raise ResourceClaimConflictError(
                resource_id, resource_type, existing.tenant_id
            )

        claim = ResourceClaim(
            id=uuid4(),
            tenant_id=tenant_id,
            resource_id=resource_id,
            resource_type=resource_type,
            source_service=source_service,
            claimed_at=datetime.now(timezone.utc),
        )
        try:
            self._session.add(claim)
            await self._session.flush()
            await self._session.refresh(claim)
        except IntegrityError:
            await self._session.rollback()
            existing = await self.get_owner(resource_id, resource_type)
            if existing and existing.tenant_id != tenant_id:
                raise ResourceClaimConflictError(
                    resource_id, resource_type, existing.tenant_id
                ) from None
            if existing:
                return existing
            raise
        return claim

    async def release(
        self, tenant_id: UUID, resource_id: str, resource_type: str
    ) -> None:
        await self._session.execute(
            delete(ResourceClaim).where(
                ResourceClaim.tenant_id == tenant_id,
                ResourceClaim.resource_id == resource_id,
                ResourceClaim.resource_type == resource_type,
            )
        )
        await self._session.flush()

    async def get_owner(
        self, resource_id: str, resource_type: str
    ) -> ResourceClaim | None:
        result = await self._session.execute(
            select(ResourceClaim).where(
                ResourceClaim.resource_id == resource_id,
                ResourceClaim.resource_type == resource_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[ResourceClaim]:
        base_where = [ResourceClaim.tenant_id == tenant_id]

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
        )
        total: int = total_result.scalar() or 0

        q = (
            select(ResourceClaim)
            .where(*base_where)
            .order_by(ResourceClaim.claimed_at.desc(), ResourceClaim.id.desc())
        )

        if next_cursor:
            cursor_dt, cursor_id = decode_cursor(next_cursor)
            q = q.where(
                or_(
                    ResourceClaim.claimed_at < cursor_dt,
                    (ResourceClaim.claimed_at == cursor_dt)
                    & (ResourceClaim.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        cursor = (
            encode_cursor(items[-1].claimed_at, items[-1].id)
            if has_more and items
            else None
        )
        return PageResult(
            items=items, total=total, has_more=has_more, next_cursor=cursor
        )

    async def bulk_claim(
        self,
        tenant_id: UUID,
        claims: list[dict[str, str]],
        source_service: str,
    ) -> list[ResourceClaim]:
        results: list[ResourceClaim] = []
        for item in claims:
            result = await self.claim(
                tenant_id,
                item["resource_id"],
                item["resource_type"],
                source_service,
            )
            results.append(result)
        return results
