"""Integration tests — ProvisioningService against a real in-memory SQLite DB.

Celery is mocked so no broker is required. Every other operation (DB reads/writes,
repository methods, domain validation) runs against real SQLAlchemy.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus
from app.domain.exceptions import (
    ProvisioningJobAlreadyActiveError,
    ProvisioningJobNotFoundError,
    ProvisioningValidationError,
    TenantProvisioningNotFoundError,
)
from app.models.provisioning_job import ProvisioningJob
from app.services.provisioning_service import ProvisioningService


@pytest.fixture
def svc(session: AsyncSession, mocker: object) -> ProvisioningService:
    mocker.patch(  # type: ignore[attr-defined]
        "app.tasks.provisioning_tasks.run_provisioning.apply_async",
        return_value=type("T", (), {"id": str(uuid4())})(),
    )
    return ProvisioningService(session)


# ── start_provisioning ────────────────────────────────────────────────────────

async def test_start_provisioning_creates_job(svc: ProvisioningService) -> None:
    tid = uuid4()
    job = await svc.start_provisioning(tid)
    assert isinstance(job, ProvisioningJob)
    assert job.tenant_id == tid
    assert job.status == JobStatus.PENDING
    assert job.total_steps == 8
    assert job.completed_steps == []
    assert job.current_step is None


async def test_start_provisioning_stores_metadata(svc: ProvisioningService) -> None:
    tid = uuid4()
    job = await svc.start_provisioning(tid, metadata={"plan": "enterprise"})
    assert job.tenant_id == tid


async def test_start_provisioning_raises_when_active_job_exists(
    svc: ProvisioningService,
) -> None:
    tid = uuid4()
    await svc.start_provisioning(tid)
    with pytest.raises(ProvisioningJobAlreadyActiveError):
        await svc.start_provisioning(tid)


async def test_start_provisioning_rejects_reserved_metadata_key(
    svc: ProvisioningService,
) -> None:
    with pytest.raises(ProvisioningValidationError):
        await svc.start_provisioning(uuid4(), metadata={"tenant_id": "stolen"})


# ── get_job ───────────────────────────────────────────────────────────────────

async def test_get_job_returns_job(svc: ProvisioningService) -> None:
    tid = uuid4()
    created = await svc.start_provisioning(tid)
    fetched = await svc.get_job(created.id)
    assert fetched.id == created.id
    assert fetched.tenant_id == tid


async def test_get_job_raises_when_not_found(svc: ProvisioningService) -> None:
    with pytest.raises(ProvisioningJobNotFoundError):
        await svc.get_job(uuid4())


# ── list_jobs ─────────────────────────────────────────────────────────────────

async def test_list_jobs_empty(svc: ProvisioningService) -> None:
    page = await svc.list_jobs()
    assert page.items == []
    assert page.total == 0
    assert page.has_more is False


async def test_list_jobs_returns_created_jobs(svc: ProvisioningService) -> None:
    t1, t2 = uuid4(), uuid4()
    await svc.start_provisioning(t1)
    await svc.start_provisioning(t2)
    page = await svc.list_jobs()
    assert page.total == 2
    assert len(page.items) == 2


async def test_list_jobs_filter_by_tenant(svc: ProvisioningService) -> None:
    t1, t2 = uuid4(), uuid4()
    await svc.start_provisioning(t1)
    await svc.start_provisioning(t2)
    page = await svc.list_jobs(tenant_id=t1)
    assert page.total == 1
    assert page.items[0].tenant_id == t1


async def test_list_jobs_filter_by_status(svc: ProvisioningService) -> None:
    await svc.start_provisioning(uuid4())
    page = await svc.list_jobs(status="pending")
    assert page.total == 1
    page_running = await svc.list_jobs(status="running")
    assert page_running.total == 0


async def test_list_jobs_cursor_pagination(svc: ProvisioningService) -> None:
    for _ in range(5):
        await svc.start_provisioning(uuid4())
    page1 = await svc.list_jobs(limit=3)
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert page1.next_cursor is not None

    page2 = await svc.list_jobs(limit=3, next_cursor=page1.next_cursor)
    assert len(page2.items) == 2
    assert page2.has_more is False

    all_ids = {j.id for j in page1.items} | {j.id for j in page2.items}
    assert len(all_ids) == 5


async def test_list_jobs_rejects_invalid_status_filter(svc: ProvisioningService) -> None:
    with pytest.raises(ProvisioningValidationError):
        await svc.list_jobs(status="bogus")


# ── retry_provisioning ────────────────────────────────────────────────────────

async def test_retry_provisioning_404_no_prior_job(svc: ProvisioningService) -> None:
    with pytest.raises(TenantProvisioningNotFoundError):
        await svc.retry_provisioning(uuid4())


async def test_retry_provisioning_422_non_failed_job(
    svc: ProvisioningService, session: AsyncSession
) -> None:
    tid = uuid4()
    await svc.start_provisioning(tid)
    with pytest.raises(ProvisioningValidationError):
        await svc.retry_provisioning(tid)


async def test_retry_provisioning_creates_new_job(
    svc: ProvisioningService, session: AsyncSession
) -> None:
    tid = uuid4()
    first = await svc.start_provisioning(tid)

    from app.repositories.provisioning_job import ProvisioningJobRepository
    repo = ProvisioningJobRepository(session)
    await repo.update_status(first.id, status=JobStatus.FAILED, error_message="infra error")
    await session.commit()

    retry_job = await svc.retry_provisioning(tid)
    assert retry_job.id != first.id
    assert retry_job.tenant_id == tid
    assert retry_job.status == JobStatus.PENDING


# ── add_resource ──────────────────────────────────────────────────────────────

async def test_add_resource_creates_record(svc: ProvisioningService) -> None:
    tid = uuid4()
    resource = await svc.add_resource(
        tid,
        resource_type="database_schema",
        resource_id=f"schema_{tid}",
        status="provisioned",
    )
    assert resource.tenant_id == tid
    assert resource.resource_type == "database_schema"
    assert resource.status == "provisioned"


async def test_add_resource_rejects_invalid_type(svc: ProvisioningService) -> None:
    with pytest.raises(ProvisioningValidationError):
        await svc.add_resource(
            uuid4(),
            resource_type="not_a_type",
            resource_id="some-id",
        )


# ── get_tenant_status ─────────────────────────────────────────────────────────

async def test_get_tenant_status_returns_job_and_resources(
    svc: ProvisioningService,
) -> None:
    tid = uuid4()
    job = await svc.start_provisioning(tid)
    await svc.add_resource(
        tid,
        resource_type="database_schema",
        resource_id=f"schema_{tid}",
    )
    latest, resources = await svc.get_tenant_status(tid)
    assert latest.id == job.id
    assert len(resources) == 1
    assert resources[0].resource_type == "database_schema"


async def test_get_tenant_status_raises_for_unknown_tenant(
    svc: ProvisioningService,
) -> None:
    with pytest.raises(TenantProvisioningNotFoundError):
        await svc.get_tenant_status(uuid4())
