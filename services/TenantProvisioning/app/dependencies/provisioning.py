"""Reusable FastAPI dependency injections for provisioning resources."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ProvisioningJobNotFoundError, TenantProvisioningNotFoundError
from app.infrastructure.database.dependencies import get_db
from app.models.provisioning_job import ProvisioningJob
from app.repositories.provisioning_job import ProvisioningJobRepository

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_job_or_404(job_id: UUID, db: DbDep) -> ProvisioningJob:
    repo = ProvisioningJobRepository(db)
    job = await repo.get_by_id(job_id)
    if job is None:
        raise ProvisioningJobNotFoundError(job_id)
    return job


async def get_active_job_or_404(tenant_id: UUID, db: DbDep) -> ProvisioningJob:
    repo = ProvisioningJobRepository(db)
    job = await repo.get_active_by_tenant_id(tenant_id)
    if job is None:
        raise TenantProvisioningNotFoundError(tenant_id)
    return job


JobDep = Annotated[ProvisioningJob, Depends(get_job_or_404)]
