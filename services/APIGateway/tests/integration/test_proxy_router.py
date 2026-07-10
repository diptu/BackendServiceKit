"""Integration tests for the proxy router.

Upstream services are mocked via httpx.MockTransport — no real network connections.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest_asyncio
from jose import jwt
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"


def _access_token(tenant_id: str) -> str:
    """Mint a token matching exactly what Authentication issues — see
    services/Authentication/app/services/token_service.py. The gateway only
    ever verifies these; it never mints them itself."""
    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": tenant_id,
        "user_id": str(uuid.uuid4()),
        "sub": tenant_id,
        "scopes": [],
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "type": "access",
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm))


def _auth_headers(tenant_id: str = _TENANT_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token(tenant_id)}"}


_TENANT_DETAIL = {
    "id": _TENANT_ID,
    "name": "Acme Corp",
    "status": "active",
}

_LIFECYCLE_STATE = {
    "tenant_id": _TENANT_ID,
    "current_status": "active",
    "previous_status": "pending",
}

_LIFECYCLE_HISTORY = {
    "tenant_id": _TENANT_ID,
    "events": [],
    "total": 0,
    "has_more": False,
    "next_cursor": None,
}

_TENANTS_LIST = {"items": [_TENANT_DETAIL], "total": 1}

_ISOLATION_VALIDATE = {
    "decision": "allow",
    "violations": [],
    "caller_tenant_id": _TENANT_ID,
    "resource_type": "document",
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    """Single dispatcher for all mocked upstream requests."""
    path = request.url.path

    # --- /api/v1/tenants ---
    if path == f"/api/v1/tenants/{_TENANT_ID}":
        if request.method == "GET":
            return httpx.Response(200, json=_TENANT_DETAIL)
        if request.method in ("PUT", "PATCH"):
            return httpx.Response(200, json={**_TENANT_DETAIL, "name": "Updated Corp"})

    if path == "/api/v1/tenants":
        if request.method == "GET":
            return httpx.Response(200, json=_TENANTS_LIST)
        if request.method == "POST":
            return httpx.Response(201, json=_TENANT_DETAIL)

    # --- /api/v1/lifecycle ---
    if path == f"/api/v1/lifecycle/{_TENANT_ID}/history":
        return httpx.Response(200, json=_LIFECYCLE_HISTORY)

    if path == f"/api/v1/lifecycle/{_TENANT_ID}/activate":
        return httpx.Response(200, json=_LIFECYCLE_STATE)

    if path == f"/api/v1/lifecycle/{_TENANT_ID}/provisioning":
        return httpx.Response(200, json={**_LIFECYCLE_STATE, "current_status": "provisioning"})

    # --- /api/v1/isolation ---
    if path == "/api/v1/isolation/validate":
        return httpx.Response(200, json=_ISOLATION_VALIDATE)

    if path == "/api/v1/isolation/check-access":
        return httpx.Response(200, json={"decision": "allow", "reason": "same-tenant"})

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
# Tenants proxy
# ---------------------------------------------------------------------------


async def test_proxy_get_tenant_returns_upstream_response(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["id"] == _TENANT_ID
    assert resp.json()["status"] == "active"


async def test_proxy_get_tenant_is_cache_miss_first_time(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    assert resp.headers.get("x-cache") == "MISS"


async def test_proxy_get_tenant_is_cache_hit_second_time(proxy_client: AsyncClient) -> None:
    await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    assert resp.headers.get("x-cache") == "HIT"
    assert resp.json()["id"] == _TENANT_ID


async def test_proxy_post_tenant_returns_201(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.post(
        "/api/v1/tenants", json={"name": "New Corp"}, headers=_auth_headers()
    )
    assert resp.status_code == 201
    assert resp.headers.get("x-cache") == "BYPASS"


async def test_proxy_put_tenant_returns_200(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.put(
        f"/api/v1/tenants/{_TENANT_ID}",
        json={"name": "Updated Corp"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Corp"


async def test_proxy_get_tenants_list(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/api/v1/tenants", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# Lifecycle proxy  (new path: /api/v1/lifecycle/*)
# ---------------------------------------------------------------------------


async def test_proxy_get_lifecycle_history(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(
        f"/api/v1/lifecycle/{_TENANT_ID}/history", headers=_auth_headers()
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == _TENANT_ID
    assert body["total"] == 0


async def test_proxy_lifecycle_get_cached_on_second_call(proxy_client: AsyncClient) -> None:
    await proxy_client.get(f"/api/v1/lifecycle/{_TENANT_ID}/history", headers=_auth_headers())
    resp = await proxy_client.get(
        f"/api/v1/lifecycle/{_TENANT_ID}/history", headers=_auth_headers()
    )
    assert resp.headers.get("x-cache") == "HIT"


async def test_proxy_lifecycle_activate_bypasses_cache(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.put(
        f"/api/v1/lifecycle/{_TENANT_ID}/activate",
        json={},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.headers.get("x-cache") == "BYPASS"


# ---------------------------------------------------------------------------
# Isolation proxy  (new: /api/v1/isolation/*)
# ---------------------------------------------------------------------------


async def test_proxy_isolation_validate(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.post(
        "/api/v1/isolation/validate",
        json={
            "caller_tenant_id": _TENANT_ID,
            "resource_ids": ["res-1"],
            "resource_type": "document",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"
    assert resp.headers.get("x-cache") == "BYPASS"


async def test_proxy_isolation_check_access(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.post(
        "/api/v1/isolation/check-access",
        json={
            "caller_tenant_id": _TENANT_ID,
            "target_tenant_id": _TENANT_ID,
            "resource_id": "res-1",
            "resource_type": "document",
            "action": "read",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "allow"


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


async def test_write_invalidates_tenant_cache(
    proxy_client: AsyncClient, fake_redis: FakeRedis
) -> None:
    # Prime cache
    await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    resp2 = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    assert resp2.headers.get("x-cache") == "HIT"

    # Write triggers invalidation — the verified token's tenant_id is what
    # drives invalidation now, not a client-supplied X-Tenant-ID.
    await proxy_client.put(
        f"/api/v1/tenants/{_TENANT_ID}",
        json={"name": "Updated Corp"},
        headers=_auth_headers(),
    )

    # Next GET is a fresh miss
    resp4 = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}", headers=_auth_headers())
    assert resp4.headers.get("x-cache") == "MISS"


# ---------------------------------------------------------------------------
# Unknown path
# ---------------------------------------------------------------------------


async def test_proxy_unknown_path_returns_404(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/api/v1/unknown-service/foo", headers=_auth_headers())
    assert resp.status_code == 404
    assert "No upstream route found" in resp.json()["detail"]


async def test_old_tenant_lifecycle_path_returns_404(proxy_client: AsyncClient) -> None:
    """The legacy /api/v1/tenant-lifecycle path is no longer registered."""
    resp = await proxy_client.get(
        f"/api/v1/tenant-lifecycle/{_TENANT_ID}/history", headers=_auth_headers()
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Gateway trust boundary — no token, invalid token
# ---------------------------------------------------------------------------


async def test_proxy_without_bearer_token_401s(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(f"/api/v1/tenants/{_TENANT_ID}")
    assert resp.status_code == 401


async def test_proxy_with_garbage_token_401s(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get(
        f"/api/v1/tenants/{_TENANT_ID}",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


async def test_proxy_ignores_client_supplied_tenant_header(fake_redis: FakeRedis) -> None:
    """A caller cannot override the tenant by setting X-Tenant-ID directly —
    only the verified token's tenant_id is trusted (this is the fix for the
    finding this whole gate exists to close)."""
    real_tenant = _TENANT_ID
    spoofed_tenant = str(uuid.uuid4())
    seen_tenant_header: list[str | None] = []

    def _capturing_handler(request: httpx.Request) -> httpx.Response:
        seen_tenant_header.append(request.headers.get("X-Tenant-ID"))
        return httpx.Response(200, json=_TENANT_DETAIL)

    app.state.redis = fake_redis
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_capturing_handler))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(
            f"/api/v1/tenants/{real_tenant}",
            headers={
                **_auth_headers(real_tenant),
                "X-Tenant-ID": spoofed_tenant,
            },
        )

    await app.state.http_client.aclose()
    app.state.http_client = None
    app.state.redis = None

    assert resp.status_code == 200
    assert seen_tenant_header == [real_tenant]


# ---------------------------------------------------------------------------
# Gateway management endpoints are NOT proxied
# ---------------------------------------------------------------------------


async def test_gateway_routes_endpoint_not_proxied(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/api/v1/gateway/routes")
    assert resp.status_code == 200
    body = resp.json()
    assert "routes" in body
    assert body["total"] == 26


async def test_health_endpoint_not_proxied(proxy_client: AsyncClient) -> None:
    resp = await proxy_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
