"""E2E tests — full provisioning flow.

Strategy: the API creates the job (tests the HTTP + service + DB write path),
then we directly await _provision_async (the task body) in-process to test all
8 provisioning steps without the asyncio.run() incompatibility of eager mode.
External HTTP to TenantLifecycle is mocked throughout.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app
from app.tasks.provisioning_tasks import _provision_async

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False)


async def _override_db() -> AsyncGenerator[AsyncSession, None]:
    async with _SESSION_FACTORY() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise


@pytest.fixture(autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(mocker: object) -> AsyncGenerator[AsyncClient, None]:
    # Celery apply_async — do not execute the task; tests drive _provision_async directly
    mocker.patch(  # type: ignore[attr-defined]
        "app.tasks.provisioning_tasks.run_provisioning.apply_async",
        return_value=type("T", (), {"id": str(uuid4())})(),
    )
    # Redirect the task's SessionLocal to our test DB
    mocker.patch(  # type: ignore[attr-defined]
        "app.tasks.provisioning_tasks.SessionLocal",
        _SESSION_FACTORY,
    )
    # Mock external HTTP call to TenantLifecycle
    mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.clients.tenant_lifecycle.TenantLifecycleClient.advance_to_pending",
        return_value=None,
    )
    # Mock rollback task dispatch (fired on failure)
    mocker.patch(  # type: ignore[attr-defined]
        "app.tasks.provisioning_tasks.rollback_provisioning.apply_async",
        return_value=None,
    )

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── helpers ───────────────────────────────────────────────────────────────────


async def _run_task(job_id: str, tenant_id: str) -> dict[str, str]:
    """Execute the provisioning task body directly in the test event loop."""
    return await _provision_async(UUID(job_id), UUID(tenant_id))


# ── tests ─────────────────────────────────────────────────────────────────────


async def test_full_provisioning_flow_completes(client: AsyncClient) -> None:
    """API creates job → _provision_async runs all 8 steps → status=completed."""
    tenant_id = str(uuid4())
    create_resp = await client.post(
        "/api/v1/provisioning/tenants",
        json={"tenant_id": tenant_id},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    result = await _run_task(job_id, tenant_id)
    assert result["status"] == "completed"

    job_resp = await client.get(f"/api/v1/provisioning/jobs/{job_id}")
    assert job_resp.status_code == 200
    job = job_resp.json()
    assert job["status"] == "completed"
    assert len(job["completed_steps"]) == 8
    assert job["current_step"] is None
    assert job["completed_at"] is not None


async def test_full_flow_creates_seven_resources(client: AsyncClient) -> None:
    """After a complete run, 7 resources (all non-FINALIZE steps) must exist."""
    tenant_id = str(uuid4())
    r = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": tenant_id})
    job_id = r.json()["id"]
    await _run_task(job_id, tenant_id)

    status_resp = await client.get(f"/api/v1/provisioning/tenants/{tenant_id}/status")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["latest_job"]["status"] == "completed"
    assert len(body["resources"]) == 7


async def test_full_flow_calls_tl_advance_to_pending(
    client: AsyncClient, mocker: object
) -> None:
    """advance_to_pending must be invoked exactly once on job completion."""
    tl_mock = mocker.patch(  # type: ignore[attr-defined]
        "app.infrastructure.clients.tenant_lifecycle.TenantLifecycleClient.advance_to_pending",
        return_value=None,
    )
    tenant_id = str(uuid4())
    r = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": tenant_id})
    job_id = r.json()["id"]
    await _run_task(job_id, tenant_id)
    tl_mock.assert_called_once()


async def test_cannot_start_second_job_while_pending(client: AsyncClient) -> None:
    """A second POST for the same tenant must return 409 when job is PENDING."""
    tenant_id = str(uuid4())
    r1 = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": tenant_id})
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": tenant_id})
    assert r2.status_code == 409
    assert r2.json()["error_code"] == "PROVISIONING_JOB_ALREADY_ACTIVE"


async def test_x_request_id_header_propagated(client: AsyncClient) -> None:
    """Responses must echo back the X-Request-ID header."""
    req_id = "e2e-trace-id-abc"
    resp = await client.post(
        "/api/v1/provisioning/tenants",
        json={"tenant_id": str(uuid4())},
        headers={"X-Request-ID": req_id},
    )
    assert resp.headers.get("X-Request-ID") == req_id


async def test_retry_after_task_failure(client: AsyncClient) -> None:
    """After a task marks a job FAILED, retry must create a new PENDING job."""
    tenant_id = str(uuid4())
    r = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": tenant_id})
    job_id = r.json()["id"]

    # Force the job to FAILED state via the repository
    async with _SESSION_FACTORY() as session:
        from app.repositories.provisioning_job import ProvisioningJobRepository
        from app.domain.enums import JobStatus
        repo = ProvisioningJobRepository(session)
        await repo.update_status(
            UUID(job_id),
            status=JobStatus.FAILED,
            error_message="simulated failure",
        )
        await session.commit()

    retry_resp = await client.post(
        f"/api/v1/provisioning/tenants/{tenant_id}/retry", json={}
    )
    assert retry_resp.status_code == 202
    retry_body = retry_resp.json()
    assert retry_body["id"] != job_id
    assert retry_body["status"] == "pending"


async def test_provisioning_list_after_completion(client: AsyncClient) -> None:
    """After task completes, GET /jobs returns the job with status=completed."""
    tenant_id = str(uuid4())
    r = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": tenant_id})
    job_id = r.json()["id"]
    await _run_task(job_id, tenant_id)

    resp = await client.get("/api/v1/provisioning/jobs", params={"tenant_id": tenant_id})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "completed"
