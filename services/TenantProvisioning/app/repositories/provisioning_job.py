"""Repository for ProvisioningJob persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

_UNSET: Any = object()

from sqlalchemy import func, or_, select, update

from app.domain.enums import JobStatus
from app.models.provisioning_job import ProvisioningJob
from app.repositories.base import BaseRepository, PageResult, decode_cursor, encode_cursor


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

    async def get_by_id(self, job_id: UUID) -> ProvisioningJob | None:
        result = await self._session.execute(
            select(ProvisioningJob).where(ProvisioningJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_by_tenant_id(self, tenant_id: UUID) -> ProvisioningJob | None:
        result = await self._session.execute(
            select(ProvisioningJob)
            .where(ProvisioningJob.tenant_id == tenant_id)
            .order_by(ProvisioningJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_by_tenant_id(self, tenant_id: UUID) -> ProvisioningJob | None:
        """Return the pending or running job for a tenant, if any."""
        result = await self._session.execute(
            select(ProvisioningJob).where(
                ProvisioningJob.tenant_id == tenant_id,
                ProvisioningJob.status.in_(
                    [JobStatus.PENDING.value, JobStatus.RUNNING.value]
                ),
            )
        )
        return result.scalar_one_or_none()

    async def has_active_job(self, tenant_id: UUID) -> bool:
        result = await self._session.execute(
            select(func.count()).where(
                ProvisioningJob.tenant_id == tenant_id,
                ProvisioningJob.status.in_(
                    [JobStatus.PENDING.value, JobStatus.RUNNING.value]
                ),
            )
        )
        return (result.scalar() or 0) > 0

    async def list(
        self,
        *,
        tenant_id: UUID | None = None,
        status: str | None = None,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[ProvisioningJob]:
        base_where = []
        if tenant_id is not None:
            base_where.append(ProvisioningJob.tenant_id == tenant_id)
        if status is not None:
            base_where.append(ProvisioningJob.status == status)

        total_result = await self._session.execute(
            select(func.count()).where(*base_where)
            if base_where
            else select(func.count(ProvisioningJob.id))
        )
        total: int = total_result.scalar() or 0

        q = select(ProvisioningJob).order_by(
            ProvisioningJob.created_at.desc(), ProvisioningJob.id.desc()
        )
        if base_where:
            q = q.where(*base_where)

        if next_cursor:
            cursor_dt, cursor_id = decode_cursor(next_cursor)
            q = q.where(
                or_(
                    ProvisioningJob.created_at < cursor_dt,
                    (ProvisioningJob.created_at == cursor_dt)
                    & (ProvisioningJob.id < cursor_id),
                )
            )

        q = q.limit(limit + 1)
        rows = (await self._session.execute(q)).scalars().all()

        has_more = len(rows) > limit
        items = list(rows[:limit])
        cursor = (
            encode_cursor(items[-1].created_at, items[-1].id) if has_more and items else None
        )
        return PageResult(items=items, total=total, has_more=has_more, next_cursor=cursor)

    async def update_status(
        self,
        job_id: UUID,
        *,
        status: str,
        current_step: str | None = _UNSET,
        completed_steps: list[str] | None = None,
        error_message: str | None = None,
        celery_task_id: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        values: dict = {"status": status, "updated_at": func.now()}
        if current_step is not _UNSET:
            values["current_step"] = current_step
        if completed_steps is not None:
            values["completed_steps"] = completed_steps
        if error_message is not None:
            values["error_message"] = error_message
        if celery_task_id is not None:
            values["celery_task_id"] = celery_task_id
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        await self._session.execute(
            update(ProvisioningJob).where(ProvisioningJob.id == job_id).values(**values)
        )
        await self._session.flush()

        from app.infrastructure.cache.redis_cache import cache_delete, job_cache_key
        await cache_delete(job_cache_key(str(job_id)))
