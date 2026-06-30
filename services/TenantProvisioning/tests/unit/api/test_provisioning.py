"""Provisioning API unit tests using in-memory SQLite."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _SESSION_FACTORY() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
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
    mocker.patch(  # type: ignore[attr-defined]
        "app.tasks.provisioning_tasks.run_provisioning.apply_async",
        return_value=type("Task", (), {"id": str(uuid4())})(),
    )
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


_TENANT_ID = str(uuid4())


async def test_start_provisioning_returns_201(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/provisioning/tenants",
        json={"tenant_id": _TENANT_ID},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tenant_id"] == _TENANT_ID
    assert body["status"] == "pending"
    assert body["total_steps"] == 8
    assert body["completed_steps"] == []
    assert body["current_step"] is None


async def test_start_provisioning_409_when_active_job_exists(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    resp = await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "PROVISIONING_JOB_ALREADY_ACTIVE"


async def test_get_job_by_id(client: AsyncClient) -> None:
    create_resp = await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    job_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/provisioning/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


async def test_get_job_404(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/provisioning/jobs/{uuid4()}")
    assert resp.status_code == 404


async def test_list_jobs_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/provisioning/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["has_more"] is False


async def test_list_jobs_returns_created_job(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    resp = await client.get("/api/v1/provisioning/jobs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert len(resp.json()["items"]) == 1


async def test_list_jobs_filter_by_tenant(client: AsyncClient) -> None:
    other_tenant = str(uuid4())
    await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": other_tenant}
    )
    resp = await client.get(
        "/api/v1/provisioning/jobs", params={"tenant_id": _TENANT_ID}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_get_tenant_status(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    resp = await client.get(f"/api/v1/provisioning/tenants/{_TENANT_ID}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == _TENANT_ID
    assert body["latest_job"] is not None
    assert body["resources"] == []


async def test_get_tenant_status_404_unknown_tenant(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/provisioning/tenants/{uuid4()}/status")
    assert resp.status_code == 404


async def test_add_resource_201(client: AsyncClient) -> None:
    resp = await client.post(
        f"/api/v1/provisioning/tenants/{_TENANT_ID}/resources",
        json={
            "resource_type": "database_schema",
            "resource_id": f"schema_{_TENANT_ID}",
            "status": "provisioned",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tenant_id"] == _TENANT_ID
    assert body["resource_type"] == "database_schema"
    assert body["status"] == "provisioned"


async def test_start_provisioning_422_reserved_metadata_key(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/provisioning/tenants",
        json={"tenant_id": _TENANT_ID, "metadata": {"tenant_id": "stolen"}},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "PROVISIONING_VALIDATION_ERROR"


async def test_list_jobs_422_invalid_status_filter(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/provisioning/jobs", params={"status": "bogus"})
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "PROVISIONING_VALIDATION_ERROR"


async def test_add_resource_422_unknown_resource_type(client: AsyncClient) -> None:
    resp = await client.post(
        f"/api/v1/provisioning/tenants/{_TENANT_ID}/resources",
        json={"resource_type": "unknown_type", "resource_id": "some-id"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "PROVISIONING_VALIDATION_ERROR"


async def test_retry_provisioning_404_no_prior_job(client: AsyncClient) -> None:
    resp = await client.post(
        f"/api/v1/provisioning/tenants/{uuid4()}/retry", json={}
    )
    assert resp.status_code == 404


async def test_retry_422_when_last_job_not_failed(client: AsyncClient) -> None:
    # The created job lands in PENDING status (Celery is mocked).
    # Retrying a non-FAILED job is a domain violation → 422.
    await client.post(
        "/api/v1/provisioning/tenants", json={"tenant_id": _TENANT_ID}
    )
    resp = await client.post(
        f"/api/v1/provisioning/tenants/{_TENANT_ID}/retry", json={}
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "PROVISIONING_VALIDATION_ERROR"
