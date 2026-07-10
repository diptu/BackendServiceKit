"""ProvisioningService — the physical database-per-tenant workflow.

Orchestrates the steps that turn a tenant record into a live, isolated
database: create the database, migrate every managed service's schema into it,
and register the connection in the Control Plane. Each step is recorded on the
ProvisioningJob so a run is observable, idempotent (a completed tenant is not
re-provisioned), and retryable after a failure.

The workflow runs inline here; a production deployment would run it on a
background worker (Celery/RQ) and this method would enqueue it. The three
collaborators — provisioner, migration runner, registrar — are injected so the
whole workflow is exercised in tests against real SQLite files with no network.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.commands import ProvisionTenantCmd
from app.domain.enums import ProvisioningStatus, ProvisioningStep
from app.domain.exceptions import (
    ProvisioningInProgressError,
    ProvisioningJobNotFoundError,
)
from app.infrastructure.control_plane import ControlPlaneRegistrar
from app.infrastructure.provisioner import DatabaseProvisioner
from app.models.provisioning_job import ProvisioningJob
from app.repositories.base import PageResult
from app.repositories.provisioning_job import ProvisioningJobRepository
from app.services.migration_runner import MigrationRunner


class ProvisioningService:
    def __init__(
        self,
        session: AsyncSession,
        provisioner: DatabaseProvisioner,
        migration_runner: MigrationRunner,
        registrar: ControlPlaneRegistrar,
    ) -> None:
        self._session = session
        self._repo = ProvisioningJobRepository(session)
        self._provisioner = provisioner
        self._migrations = migration_runner
        self._registrar = registrar

    async def provision(self, cmd: ProvisionTenantCmd) -> ProvisioningJob:
        existing = await self._repo.get_by_tenant_id(cmd.tenant_id)
        if existing is not None:
            if existing.status == ProvisioningStatus.COMPLETED.value:
                return existing  # idempotent — already provisioned
            if existing.status == ProvisioningStatus.RUNNING.value:
                raise ProvisioningInProgressError(cmd.tenant_id)
            job = existing
            job.subdomain = cmd.subdomain
            job.region = cmd.region
        else:
            job = await self._repo.create(
                ProvisioningJob(
                    tenant_id=cmd.tenant_id,
                    subdomain=cmd.subdomain,
                    region=cmd.region,
                    status=ProvisioningStatus.PENDING.value,
                )
            )
        return await self._run_workflow(job)

    async def get(self, tenant_id: uuid.UUID) -> ProvisioningJob:
        job = await self._repo.get_by_tenant_id(tenant_id)
        if job is None:
            raise ProvisioningJobNotFoundError(tenant_id)
        return job

    async def list(
        self, *, status: str | None = None, cursor: str | None = None, limit: int = 20
    ) -> PageResult[ProvisioningJob]:
        return await self._repo.list(status=status, cursor=cursor, limit=limit)

    async def retry(self, tenant_id: uuid.UUID) -> ProvisioningJob:
        job = await self.get(tenant_id)
        if job.status == ProvisioningStatus.COMPLETED.value:
            return job
        if job.status == ProvisioningStatus.RUNNING.value:
            raise ProvisioningInProgressError(tenant_id)
        return await self._run_workflow(job)

    async def deprovision(self, tenant_id: uuid.UUID) -> ProvisioningJob:
        job = await self.get(tenant_id)
        await self._registrar.deprovision(tenant_id)
        await self._provisioner.drop(tenant_id)
        job.status = ProvisioningStatus.DEPROVISIONED.value
        job.current_step = None
        return await self._repo.save(job)

    async def _run_workflow(self, job: ProvisioningJob) -> ProvisioningJob:
        job.status = ProvisioningStatus.RUNNING.value
        job.attempts += 1
        job.error = None
        await self._repo.save(job)

        try:
            job.current_step = ProvisioningStep.CREATE_DATABASE.value
            await self._repo.save(job)
            db = await self._provisioner.create(job.tenant_id)
            job.db_name = db.name
            await self._repo.save(job)

            job.current_step = ProvisioningStep.RUN_MIGRATIONS.value
            await self._repo.save(job)
            await self._migrations.migrate(db.dsn, settings.managed_services)

            job.current_step = ProvisioningStep.REGISTER_CONTROL_PLANE.value
            await self._repo.save(job)
            await self._registrar.register(
                tenant_id=job.tenant_id,
                subdomain=job.subdomain,
                db=db,
                region=job.region,
            )

            job.current_step = ProvisioningStep.DONE.value
            job.status = ProvisioningStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            return await self._repo.save(job)
        except Exception as exc:  # noqa: BLE001 — record the failure on the job
            job.status = ProvisioningStatus.FAILED.value
            job.error = str(exc)[:1000]
            return await self._repo.save(job)
