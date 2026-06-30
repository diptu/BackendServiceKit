"""Performance tests — concurrent provisioning requests.

These tests verify the API can handle concurrent requests without data corruption.
Celery is mocked so execution stays in-process and measures API + DB throughput only.
No broker or real Celery worker is required.

Note: race-condition tests (same-tenant concurrency) use PostgreSQL semantics in
production. SQLite in-process tests serialize at the asyncio level, so we test
for the weaker invariant (≥1 success) rather than exactly-1.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.infrastructure.database.dependencies import get_db
from app.main import app
from app.middleware.rate_limit import limiter

_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
)
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
    mocker.patch(  # type: ignore[attr-defined]
        "app.tasks.provisioning_tasks.run_provisioning.apply_async",
        return_value=type("T", (), {"id": str(uuid4())})(),
    )
    # Disable rate limiting so concurrent tests don't bleed counter state
    limiter._enabled = False  # type: ignore[attr-defined]
    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    limiter._enabled = True  # type: ignore[attr-defined]
    app.dependency_overrides.clear()


async def _start(client: AsyncClient, tenant_id: str) -> int:
    resp = await client.post(
        "/api/v1/provisioning/tenants",
        json={"tenant_id": tenant_id},
    )
    return resp.status_code


async def test_concurrent_unique_tenants_all_succeed(client: AsyncClient) -> None:
    """20 concurrent requests for different tenants must all return 201."""
    tenant_ids = [str(uuid4()) for _ in range(20)]
    start = time.monotonic()
    statuses = await asyncio.gather(*[_start(client, tid) for tid in tenant_ids])
    elapsed = time.monotonic() - start

    assert all(s == 201 for s in statuses), f"Some requests failed: {statuses}"
    assert elapsed < 10.0, f"20 concurrent requests took {elapsed:.2f}s (too slow)"


async def test_concurrent_same_tenant_at_least_one_wins(client: AsyncClient) -> None:
    """Concurrent requests for the same tenant: at least 1 succeeds, none error 5xx.

    Exactly-1 is a PostgreSQL-level guarantee (SELECT FOR UPDATE / unique constraint).
    SQLite serializes at the asyncio level so additional 201s are acceptable here.
    """
    tenant_id = str(uuid4())
    statuses = await asyncio.gather(*[_start(client, tenant_id) for _ in range(10)])
    successes = statuses.count(201)
    conflicts = statuses.count(409)
    server_errors = [s for s in statuses if s >= 500]

    assert successes >= 1, "At least one request must succeed"
    assert not server_errors, f"No 5xx errors allowed: {server_errors}"
    assert successes + conflicts == len(statuses)


async def test_list_jobs_under_load(client: AsyncClient) -> None:
    """50 jobs created, then 10 concurrent GET /jobs requests all return 200."""
    for _ in range(50):
        await _start(client, str(uuid4()))

    start = time.monotonic()
    responses = await asyncio.gather(
        *[client.get("/api/v1/provisioning/jobs", params={"limit": 20}) for _ in range(10)]
    )
    elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < 5.0, f"10 concurrent list requests took {elapsed:.2f}s"
    for r in responses:
        assert r.json()["total"] == 50


async def test_queue_depth_reflects_active_jobs(client: AsyncClient) -> None:
    """After N jobs are created, GET /jobs?status=pending shows N results."""
    n = 15
    for _ in range(n):
        await _start(client, str(uuid4()))

    resp = await client.get(
        "/api/v1/provisioning/jobs", params={"status": "pending", "limit": 50}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == n


async def test_mixed_read_write_load(client: AsyncClient) -> None:
    """Interleave writes (POST /tenants) and reads (GET /jobs) concurrently."""
    write_tenants = [str(uuid4()) for _ in range(10)]
    reads = [client.get("/api/v1/provisioning/jobs") for _ in range(10)]
    writes = [_start(client, tid) for tid in write_tenants]

    results = await asyncio.gather(*writes, *reads, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, f"Errors under mixed load: {errors}"


async def test_get_job_throughput(client: AsyncClient) -> None:
    """10 sequential GET /jobs/{id} calls complete within 2 seconds."""
    r = await client.post("/api/v1/provisioning/tenants", json={"tenant_id": str(uuid4())})
    job_id = r.json()["id"]

    start = time.monotonic()
    responses = await asyncio.gather(
        *[client.get(f"/api/v1/provisioning/jobs/{job_id}") for _ in range(10)]
    )
    elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < 2.0, f"10 GET /jobs/{{id}} took {elapsed:.2f}s"
