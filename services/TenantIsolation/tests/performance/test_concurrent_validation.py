"""Performance tests — concurrent isolation endpoint calls."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.rate_limit import limiter


@pytest.fixture
async def client() -> AsyncClient:
    limiter._enabled = False
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    limiter._enabled = False


async def test_concurrent_validate_requests(client: AsyncClient) -> None:
    tid = str(uuid4())
    rid = str(uuid4())

    async def _validate() -> int:
        r = await client.post(
            "/api/v1/isolation/validate",
            json={"caller_tenant_id": tid, "resource_ids": [rid], "resource_type": "document"},
        )
        return r.status_code

    codes = await asyncio.gather(*[_validate() for _ in range(50)])
    assert all(c == 200 for c in codes)


async def test_concurrent_check_access(client: AsyncClient) -> None:
    caller = str(uuid4())
    target = str(uuid4())

    async def _check() -> int:
        r = await client.post(
            "/api/v1/isolation/check-access",
            json={
                "caller_tenant_id": caller,
                "target_tenant_id": target,
                "resource_id": "shared-resource",
                "resource_type": "document",
                "action": "read",
            },
        )
        return r.status_code

    codes = await asyncio.gather(*[_check() for _ in range(100)])
    assert all(c == 200 for c in codes)


async def test_claim_throughput(client: AsyncClient) -> None:
    tid = str(uuid4())
    results: list[int] = []
    for _ in range(20):
        r = await client.post(
            "/api/v1/isolation/claims",
            json={
                "tenant_id": tid,
                "resource_id": str(uuid4()),
                "resource_type": "document",
                "source_service": "perf-test",
            },
        )
        results.append(r.status_code)
    assert all(s == 201 for s in results)


async def test_cache_effectiveness(client: AsyncClient, mocker: object) -> None:
    caller = str(uuid4())
    target = str(uuid4())

    first_call_hit = []

    original_cache_get = None
    from app.infrastructure.cache import redis_cache

    call_count = {"n": 0}

    async def fake_cache_get(key: str) -> object:
        call_count["n"] += 1
        return None

    async def fake_cache_set(key: str, value: object, ttl: int = 60) -> None:
        pass

    mocker.patch.object(redis_cache, "cache_get", fake_cache_get)  # type: ignore[attr-defined]
    mocker.patch.object(redis_cache, "cache_set", fake_cache_set)  # type: ignore[attr-defined]

    r = await client.post(
        "/api/v1/isolation/check-access",
        json={
            "caller_tenant_id": caller,
            "target_tenant_id": target,
            "resource_id": "res-cache-test",
            "resource_type": "document",
            "action": "read",
        },
    )
    assert r.status_code == 200
    assert call_count["n"] >= 1


async def test_large_resource_list(client: AsyncClient) -> None:
    tid = str(uuid4())
    resource_ids = [str(uuid4()) for _ in range(100)]

    r = await client.post(
        "/api/v1/isolation/validate",
        json={
            "caller_tenant_id": tid,
            "resource_ids": resource_ids,
            "resource_type": "document",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "deny"
    assert len(r.json()["violations"]) == 100
