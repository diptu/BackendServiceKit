"""ProvisioningJobRepository — data access for the global job store."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, and_, select

from app.models.provisioning_job import ProvisioningJob
from app.repositories.base import (
    BaseRepository,
    PageResult,
    decode_cursor,
    encode_cursor,
)


class ProvisioningJobRepository(BaseRepository[ProvisioningJob]):
    async def create(self, job: ProvisioningJob) -> ProvisioningJob:
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def save(self, job: ProvisioningJob) -> ProvisioningJob:
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def get_by_tenant_id(self, tenant_id: UUID) -> ProvisioningJob | None:
        result = await self._session.execute(
            select(ProvisioningJob).where(ProvisioningJob.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self, *, status: str | None = None, cursor: str | None = None, limit: int = 20
    ) -> PageResult[ProvisioningJob]:
        base: Select[tuple[ProvisioningJob]] = select(ProvisioningJob)
        if status is not None:
            base = base.where(ProvisioningJob.status == status)

        total = await self._session.scalar(
            select(func.count()).select_from(base.subquery())
        )

        stmt = base
        if cursor is not None:
            cursor_dt, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    ProvisioningJob.created_at < cursor_dt,
                    and_(
                        ProvisioningJob.created_at == cursor_dt,
                        ProvisioningJob.tenant_id < cursor_id,
                    ),
                )
            )
        stmt = stmt.order_by(
            ProvisioningJob.created_at.desc(), ProvisioningJob.tenant_id.desc()
        ).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: list[ProvisioningJob] = list(result.scalars())
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.tenant_id)
        return PageResult(
            items=items,
            total=total or 0,
            next_cursor=next_cursor,
            has_more=has_more,
        )
