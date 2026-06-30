"""Integration tests for the proxy router.

The upstream services (TenantManagement, TenantLifecycle) are mocked using
httpx.MockTransport so no real network connections are made.
"""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.cache_service import CacheService

# ---------------------------------------------------------------------------
# Mock transport — returns pre-canned responses for upstream URLs
# ---------------------------------------------------------------------------

_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"

_TENANT_DETAIL = {
    "id": _TENANT_ID,
    "name": "Acme Corp",
    "status": "active",
}

_LIFECYCLE_HISTORY = {
    "tenant_id": _TENANT_ID,
    "events": [],
    "total": 0,
    "has_more": False,
    "next_cursor": None,
}

_TENANTS_LIST = {"items": [_TENANT_DETAIL], "total": 1}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    """Simple dispatcher for mocked upstream requests."""
    path = request.url.path

    if path == f"/api/v1/tenants/{_TENANT_ID}":
        if request.method == "GET":
            return httpx.Response(200, json=_TENANT_DETAIL)
        if request.method == "PUT":
            updated = {**_TENANT_DETAIL, "name": "Updated Corp"}
            return httpx.Response(200, json=updated)

    if path == "/api/v1/tenants":
        if request.method == "GET":
            return httpx.Response(200, json=_TENANTS_LIST)
        if request.method == "POST":
            return httpx.Response(201, json=_TENANT_DETAIL)

    if path == f"/api/v1/tenant-lifecycle/{_TENANT_ID}/history":
        return httpx.Response(200, json=_LIFECYCLE_HISTORY)

    if path == f"/api/v1/tenant-lifecycle/{_TENANT_ID}/activate":
        return httpx.Response(200, json={"tenant_id": _TENANT_ID, "current_status": "active"})

    return httpx.Response(404, json={"detail": "not found"})


@pytest_asyncio.fixture
async def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture
async def proxy_client(fake_redis: FakeRedis) -> AsyncClient:
    """Test client with fake Redis and a mock httpx transport for upstream calls."""
    mock_transport = httpx.MockTransport(_mock_handler)
    app.state.redis = fake_redis
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient(transport=mock_transport)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]

    await app.state.http_client.aclose()
    app.state.http_client = None
    app.state.redis = None


# ---------------------------------------------------------------------------
# TenantManagement proxy tests
# ---------------------------------------------------------------------------

async def test_proxy_get_tenant_returns_upstream_response(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == _TENANT_ID
    assert body["status"] == "active"


async def test_proxy_get_tenant_is_cache_miss_first_time(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    assert resp.headers.get("x-cache") == "MISS"


async def test_proxy_get_tenant_is_cache_hit_second_time(proxy_client: AsyncClient) -> None:
    await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    assert resp.headers.get("x-cache") == "HIT"
    assert resp.json()["id"] == _TENANT_ID


async def test_proxy_post_tenant_returns_201(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.post("/api/v1/tenants", json={"name": "New Corp"})
    assert resp.status_code == 201
    assert resp.headers.get("x-cache") == "BYPASS"


async def test_proxy_put_tenant_returns_200(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.put(
        f"/api/v1/tenants/{_TENANT_ID}",
        json={"name": "Updated Corp"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Corp"


async def test_proxy_get_tenants_list(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/api/v1/tenants")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# TenantLifecycle proxy tests
# ---------------------------------------------------------------------------

async def test_proxy_get_lifecycle_history(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(f"/api/v1/tenant-lifecycle/{_TENANT_ID}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == _TENANT_ID
    assert body["total"] == 0


async def test_proxy_lifecycle_get_cached_on_second_call(proxy_client: AsyncClient) -> None:
    await proxy_client.get(f"/api/v1/tenant-lifecycle/{_TENANT_ID}/history")
    resp = await proxy_client.get(f"/api/v1/tenant-lifecycle/{_TENANT_ID}/history")
    assert resp.headers.get("x-cache") == "HIT"


async def test_proxy_lifecycle_activate_bypasses_cache(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.put(
        f"/api/v1/tenant-lifecycle/{_TENANT_ID}/activate",
        json={},
    )
    assert resp.status_code == 200
    assert resp.headers.get("x-cache") == "BYPASS"


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------

async def test_write_invalidates_tenant_cache(proxy_client: AsyncClient, fake_redis: FakeRedis) -> None:
    """After a GET (cache miss), a PUT with X-Tenant-ID purges the cached entry."""
    # Prime the cache
    await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")

    # Verify it's now in cache
    resp2 = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    assert resp2.headers.get("x-cache") == "HIT"

    # Write with tenant ID header → triggers invalidation
    await proxy_client.put(
        f"/api/v1/tenants/{_TENANT_ID}",
        json={"name": "Updated Corp"},
        headers={"X-Tenant-ID": _TENANT_ID},
    )

    # Next GET should be a fresh miss
    resp4 = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    assert resp4.headers.get("x-cache") == "MISS"


# ---------------------------------------------------------------------------
# Unknown path
# ---------------------------------------------------------------------------

async def test_proxy_unknown_path_returns_404(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/api/v1/unknown-service/foo")
    assert resp.status_code == 404
    assert "No upstream route found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Gateway management endpoints are NOT proxied
# ---------------------------------------------------------------------------

async def test_gateway_routes_endpoint_not_proxied(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/api/v1/gateway/routes")
    assert resp.status_code == 200
    body = resp.json()
    assert "routes" in body
    assert body["total"] == 3


async def test_health_endpoint_not_proxied(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
