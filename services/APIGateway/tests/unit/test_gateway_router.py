"""Unit tests for gateway management endpoints.

Covers: /api/v1/gateway/routes, /api/v1/gateway/status,
and the Kong Admin integration endpoints (/gateway/kong/*).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# Mock data for Kong Admin API
# ---------------------------------------------------------------------------

_KONG_STATUS_BODY = {
    "version": "3.5.0",
    "hostname": "kong-test",
    "server": {"connections_accepted": 100, "connections_active": 2},
}

_KONG_SERVICES_BODY = {
    "data": [
        {
            "id": "svc-1",
            "name": "nutratenant-tenent",
            "host": "tenent",
            "port": 8000,
            "protocol": "http",
            "tags": [],
        },
        {
            "id": "svc-2",
            "name": "nutratenant-tenant-provisioning",
            "host": "provisioning",
            "port": 8000,
            "protocol": "http",
            "tags": [],
        },
    ],
    "next": None,
}

_KONG_ROUTES_BODY = {
    "data": [
        {
            "id": "rt-1",
            "name": "tenants-route",
            "paths": ["/api/v1/tenants"],
            "protocols": ["http", "https"],
            "tags": [],
        },
    ],
    "next": None,
}

_KONG_PLUGINS_BODY = {
    "data": [
        {"id": "pl-1", "name": "prometheus", "enabled": True, "tags": []},
        {"id": "pl-2", "name": "cors", "enabled": True, "tags": []},
        {"id": "pl-3", "name": "rate-limiting", "enabled": True, "tags": []},
    ],
    "next": None,
}


def _kong_ok_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    method = request.method
    if path == "/status":
        return httpx.Response(200, json=_KONG_STATUS_BODY)
    if path == "/services" and method == "GET":
        return httpx.Response(200, json=_KONG_SERVICES_BODY)
    if path == "/routes" and method == "GET":
        return httpx.Response(200, json=_KONG_ROUTES_BODY)
    if path == "/plugins" and method == "GET":
        return httpx.Response(200, json=_KONG_PLUGINS_BODY)
    if method == "PUT" and path.startswith("/services/"):
        name = path.rstrip("/").split("/")[-1]
        return httpx.Response(200, json={"id": f"id-{name}", "name": name})
    return httpx.Response(404, json={"message": "not found"})


def _kong_down_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("Kong unreachable")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_kong_transport(handler=_kong_down_handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Base test client — no Redis, no RabbitMQ, Kong unreachable."""
    app.state.redis = None
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient(transport=_make_kong_transport())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]
    await app.state.http_client.aclose()
    app.state.redis = None
    app.state.http_client = None


@pytest_asyncio.fixture
async def client_with_redis() -> AsyncClient:
    """Test client with fake Redis available."""
    app.state.redis = FakeRedis()
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient(transport=_make_kong_transport())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]
    await app.state.http_client.aclose()
    app.state.redis = None
    app.state.http_client = None


@pytest_asyncio.fixture
async def kong_client() -> AsyncClient:
    """Test client with a responding mock Kong Admin API."""
    app.state.redis = None
    app.state.rabbitmq_connection = None
    app.state.http_client = httpx.AsyncClient(transport=_make_kong_transport(_kong_ok_handler))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c  # type: ignore[misc]
    await app.state.http_client.aclose()
    app.state.redis = None
    app.state.http_client = None


@pytest.fixture
def mock_healthy_upstreams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replaces the httpx.AsyncClient created inside gateway_status with a mock
    that returns HTTP 200 for every upstream /health probe."""
    import app.api.v1.gateway_router as gw_module

    mock_inner = MagicMock()
    mock_inner.get = AsyncMock(return_value=httpx.Response(200, json={"status": "ok"}))
    mock_inner.is_success = True

    class _FakeAsyncClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> MagicMock:
            return mock_inner

        async def __aexit__(self, *args: object) -> None:
            pass

    monkeypatch.setattr(gw_module.httpx, "AsyncClient", _FakeAsyncClient)


# ---------------------------------------------------------------------------
# GET /api/v1/gateway/routes
# ---------------------------------------------------------------------------


async def test_list_routes_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gateway/routes")
    assert resp.status_code == 200


async def test_list_routes_total_matches_registry(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/routes")).json()
    assert body["total"] == 4
    assert len(body["routes"]) == 4


async def test_list_routes_includes_expected_prefixes(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/routes")).json()
    prefixes = {r["prefix"] for r in body["routes"]}
    assert prefixes == {
        "/api/v1/tenants",
        "/api/v1/lifecycle",
        "/api/v1/isolation",
        "/api/v1/provisioning",
    }


async def test_list_routes_each_route_has_required_fields(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/routes")).json()
    required = {"prefix", "upstream", "base_url", "cacheable_methods", "cache_ttl_seconds"}
    for route in body["routes"]:
        assert required.issubset(route.keys())


async def test_list_routes_cacheable_methods_is_list(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/routes")).json()
    for route in body["routes"]:
        assert isinstance(route["cacheable_methods"], list)
        assert len(route["cacheable_methods"]) > 0


async def test_list_routes_cache_ttl_is_positive(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/routes")).json()
    for route in body["routes"]:
        assert route["cache_ttl_seconds"] > 0


# ---------------------------------------------------------------------------
# GET /api/v1/gateway/status
# ---------------------------------------------------------------------------


async def test_gateway_status_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gateway/status")
    assert resp.status_code == 200


async def test_gateway_status_reports_ok(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/status")).json()
    assert body["status"] == "ok"


async def test_gateway_status_no_redis_reports_disconnected(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/status")).json()
    assert body["redis_connected"] is False


async def test_gateway_status_with_fake_redis_reports_connected(
    client_with_redis: AsyncClient,
) -> None:
    body = (await client_with_redis.get("/api/v1/gateway/status")).json()
    assert body["redis_connected"] is True


async def test_gateway_status_no_rabbitmq_reports_disconnected(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/status")).json()
    assert body["rabbitmq_connected"] is False


async def test_gateway_status_returns_version_and_environment(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/status")).json()
    assert body["version"] == "0.1.0"
    assert body["environment"] in ("development", "testing", "staging", "production")


async def test_gateway_status_upstreams_unreachable_when_no_services(
    client: AsyncClient,
) -> None:
    """Upstream /health probes all fail → each entry has reachable=False."""
    body = (await client.get("/api/v1/gateway/status")).json()
    assert len(body["upstreams"]) > 0
    for upstream in body["upstreams"]:
        assert upstream["reachable"] is False


async def test_gateway_status_probes_unique_upstreams_only(client: AsyncClient) -> None:
    """Routes sharing an upstream are de-duped — only 2 unique upstreams probed."""
    body = (await client.get("/api/v1/gateway/status")).json()
    names = [u["name"] for u in body["upstreams"]]
    assert len(names) == len(set(names)), "upstream names must be unique"
    assert len(names) == 2  # tenent + tenant_provisioning


async def test_gateway_status_upstreams_have_name_and_base_url(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/gateway/status")).json()
    for upstream in body["upstreams"]:
        assert upstream["name"]
        assert upstream["base_url"].startswith("http")


async def test_gateway_status_with_healthy_upstreams(
    client_with_redis: AsyncClient,
    mock_healthy_upstreams: None,
) -> None:
    body = (await client_with_redis.get("/api/v1/gateway/status")).json()
    assert body["redis_connected"] is True
    for upstream in body["upstreams"]:
        assert upstream["reachable"] is True
        assert upstream["status_code"] == 200
        assert upstream["latency_ms"] is not None


# ---------------------------------------------------------------------------
# GET /api/v1/gateway/kong/status
# ---------------------------------------------------------------------------


async def test_kong_status_unavailable_when_kong_unreachable(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gateway/kong/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False


async def test_kong_status_available_when_kong_reachable(kong_client: AsyncClient) -> None:
    resp = await kong_client.get("/api/v1/gateway/kong/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True


async def test_kong_status_returns_service_route_plugin_counts(
    kong_client: AsyncClient,
) -> None:
    body = (await kong_client.get("/api/v1/gateway/kong/status")).json()
    assert body["services_count"] == 2
    assert body["routes_count"] == 1
    assert body["plugins_count"] == 3


async def test_kong_status_returns_version_and_hostname(kong_client: AsyncClient) -> None:
    body = (await kong_client.get("/api/v1/gateway/kong/status")).json()
    assert body["version"] == "3.5.0"
    assert body["hostname"] == "kong-test"


# ---------------------------------------------------------------------------
# GET /api/v1/gateway/kong/services
# ---------------------------------------------------------------------------


async def test_kong_services_returns_200_with_list(kong_client: AsyncClient) -> None:
    resp = await kong_client.get("/api/v1/gateway/kong/services")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2


async def test_kong_services_contains_expected_service(kong_client: AsyncClient) -> None:
    body = (await kong_client.get("/api/v1/gateway/kong/services")).json()
    names = {s["name"] for s in body}
    assert "nutratenant-tenent" in names


async def test_kong_services_returns_503_when_unreachable(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gateway/kong/services")
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/v1/gateway/kong/routes
# ---------------------------------------------------------------------------


async def test_kong_routes_returns_200_with_list(kong_client: AsyncClient) -> None:
    resp = await kong_client.get("/api/v1/gateway/kong/routes")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_kong_routes_contains_path_field(kong_client: AsyncClient) -> None:
    body = (await kong_client.get("/api/v1/gateway/kong/routes")).json()
    assert len(body) == 1
    assert "/api/v1/tenants" in body[0]["paths"]


async def test_kong_routes_returns_503_when_unreachable(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gateway/kong/routes")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/v1/gateway/kong/plugins
# ---------------------------------------------------------------------------


async def test_kong_plugins_returns_200_with_list(kong_client: AsyncClient) -> None:
    resp = await kong_client.get("/api/v1/gateway/kong/plugins")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3


async def test_kong_plugins_includes_prometheus(kong_client: AsyncClient) -> None:
    body = (await kong_client.get("/api/v1/gateway/kong/plugins")).json()
    names = {p["name"] for p in body}
    assert "prometheus" in names


async def test_kong_plugins_returns_503_when_unreachable(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/gateway/kong/plugins")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# POST /api/v1/gateway/kong/sync
# ---------------------------------------------------------------------------


async def test_kong_sync_success_returns_sync_counts(kong_client: AsyncClient) -> None:
    resp = await kong_client.post("/api/v1/gateway/kong/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"synced", "skipped", "failed", "total"}


async def test_kong_sync_total_equals_sum_of_counts(kong_client: AsyncClient) -> None:
    body = (await kong_client.post("/api/v1/gateway/kong/sync")).json()
    assert body["total"] == len(body["synced"]) + len(body["skipped"]) + len(body["failed"])


async def test_kong_sync_syncs_all_routes_when_kong_available(
    kong_client: AsyncClient,
) -> None:
    body = (await kong_client.post("/api/v1/gateway/kong/sync")).json()
    assert len(body["synced"]) == 4
    assert len(body["failed"]) == 0


async def test_kong_sync_marks_all_failed_when_kong_unreachable(
    client: AsyncClient,
) -> None:
    resp = await client.post("/api/v1/gateway/kong/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["failed"]) == 4
    assert len(body["synced"]) == 0
