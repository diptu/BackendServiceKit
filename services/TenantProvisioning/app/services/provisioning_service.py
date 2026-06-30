"""ProvisioningService — orchestrates job creation and Celery task dispatch."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus, PROVISIONING_STEPS
from app.domain.events import ProvisioningStarted
from app.events.provisioning_events import EventPublisher, publish_event
from app.infrastructure.messaging.publisher import NullPublisher
from app.tasks.provisioning_tasks import run_provisioning  # module-level so patch() works in tests
from app.domain.exceptions import (
    ProvisioningJobAlreadyActiveError,
    ProvisioningJobNotFoundError,
    TenantProvisioningNotFoundError,
)
from app.validators.provisioning_validator import (
    validate_can_retry,
    validate_list_jobs_filter,
    validate_start_provisioning,
)
from app.validators.resource_validator import validate_add_resource
from app.models.provisioning_job import ProvisioningJob
from app.models.provisioning_resource import ProvisioningResource
from app.repositories.provisioning_job import ProvisioningJobRepository
from app.repositories.provisioning_resource import ProvisioningResourceRepository
from app.repositories.base import PageResult

logger = logging.getLogger(__name__)


class ProvisioningService:
    __slots__ = ("_job_repo", "_resource_repo", "_publisher")

    def __init__(self, session: AsyncSession, publisher: EventPublisher | None = None) -> None:
        self._job_repo = ProvisioningJobRepository(session)
        self._resource_repo = ProvisioningResourceRepository(session)
        self._publisher: EventPublisher = publisher or NullPublisher()

    async def start_provisioning(
        self,
        tenant_id: UUID,
        *,
        metadata: dict[str, str] | None = None,
    ) -> ProvisioningJob:
        """Create a new provisioning job and dispatch it to Celery.

        Raises ProvisioningJobAlreadyActiveError if a pending/running job exists.
        """
        validate_start_provisioning(metadata=metadata)
        if await self._job_repo.has_active_job(tenant_id):
            raise ProvisioningJobAlreadyActiveError(tenant_id)

        now = datetime.now(timezone.utc)
        job = ProvisioningJob(
            id=uuid4(),
            tenant_id=tenant_id,
            status=JobStatus.PENDING.value,
            completed_steps=[],
            total_steps=len(PROVISIONING_STEPS),
            created_at=now,
            updated_at=now,
        )
        job = await self._job_repo.create(job)

        await publish_event(ProvisioningStarted(tenant_id=tenant_id, job_id=job.id), self._publisher)

        task = run_provisioning.apply_async(
            args=[str(job.id), str(tenant_id)],
            ignore_result=False,
        )

        await self._job_repo.update_status(
            job.id,
            status=JobStatus.PENDING,
            celery_task_id=task.id,
        )

        logger.info(
            "provisioning_job_created",
            extra={
                "job_id": str(job.id),
                "tenant_id": str(tenant_id),
                "celery_task_id": task.id,
            },
        )
        return await self._job_repo.get_by_id(job.id) or job  # type: ignore[return-value]

    async def retry_provisioning(self, tenant_id: UUID) -> ProvisioningJob:
        """Create a new job for a previously failed provisioning attempt.

        Raises TenantProvisioningNotFoundError if tenant has no prior jobs.
        Raises CannotRetryNonFailedJobError if the last job is not FAILED.
        Raises ProvisioningJobAlreadyActiveError on concurrent retry race.
        """
        prior = await self._job_repo.get_latest_by_tenant_id(tenant_id)
        if prior is None:
            raise TenantProvisioningNotFoundError(tenant_id)
        validate_can_retry(prior)
        if await self._job_repo.has_active_job(tenant_id):
            raise ProvisioningJobAlreadyActiveError(tenant_id)

        return await self.start_provisioning(tenant_id)

    async def get_job(self, job_id: UUID) -> ProvisioningJob:
        job = await self._job_repo.get_by_id(job_id)
        if job is None:
            raise ProvisioningJobNotFoundError(job_id)
        return job

    async def list_jobs(
        self,
        *,
        tenant_id: UUID | None = None,
        status: str | None = None,
        next_cursor: str | None = None,
        limit: int = 20,
    ) -> PageResult[ProvisioningJob]:
        validate_list_jobs_filter(status=status)
        return await self._job_repo.list(
            tenant_id=tenant_id,
            status=status,
            next_cursor=next_cursor,
            limit=limit,
        )

    async def add_resource(
        self,
        tenant_id: UUID,
        *,
        resource_type: str,
        resource_id: str,
        status: str = "provisioned",
        meta: dict | None = None,
    ) -> ProvisioningResource:
        validate_add_resource(resource_type=resource_type, resource_id=resource_id, status=status)
        now = datetime.now(timezone.utc)
        resource = ProvisioningResource(
            id=uuid4(),
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            meta=meta,
            provisioned_at=now if status == "provisioned" else None,
        )
        return await self._resource_repo.create(resource)

    async def get_tenant_status(self, tenant_id: UUID) -> tuple[ProvisioningJob | None, list[ProvisioningResource]]:
        """Return the latest job and all resources for a tenant.

        Raises TenantProvisioningNotFoundError if no jobs exist.
        """
        latest = await self._job_repo.get_latest_by_tenant_id(tenant_id)
        if latest is None:
            raise TenantProvisioningNotFoundError(tenant_id)
        resources = await self._resource_repo.list_by_tenant_id(tenant_id)
        return latest, resources
