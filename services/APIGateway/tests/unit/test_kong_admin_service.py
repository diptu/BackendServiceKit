"""Unit tests for KongAdminService — all Kong Admin API interactions mocked."""

from __future__ import annotations

import httpx
import pytest

from app.services.kong_admin_service import KongAdminService, KongSyncResult

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_STATUS_BODY = {
    "server": {
        "connections_accepted": 100,
        "connections_active": 2,
        "connections_handled": 100,
        "connections_reading": 0,
        "connections_waiting": 1,
        "connections_writing": 1,
        "total_requests": 100,
    },
    "memory": {"workers_lua_vms": []},
}

_SERVICES_BODY = {
    "data": [
        {
            "id": "svc-1",
            "name": "nutratenant-tenent",
            "host": "tenent",
            "port": 8000,
            "protocol": "http",
            "tags": ["tenent"],
        },
        {
            "id": "svc-2",
            "name": "nutratenant-tenant-provisioning",
            "host": "tenant-provisioning",
            "port": 8000,
            "protocol": "http",
            "tags": ["provisioning"],
        },
    ],
    "next": None,
}

_ROUTES_BODY = {
    "data": [
        {
            "id": "rt-1",
            "name": "tenants-route",
            "paths": ["/api/v1/tenants"],
            "protocols": ["http", "https"],
            "tags": ["tenent"],
        },
        {
            "id": "rt-2",
            "name": "provisioning-route",
            "paths": ["/api/v1/provisioning"],
            "protocols": ["http", "https"],
            "tags": ["provisioning"],
        },
    ],
    "next": None,
}

_PLUGINS_BODY = {
    "data": [
        {"id": "pl-1", "name": "cors", "enabled": True, "tags": []},
        {"id": "pl-2", "name": "rate-limiting", "enabled": True, "tags": []},
        {"id": "pl-3", "name": "prometheus", "enabled": True, "tags": []},
    ],
    "next": None,
}


# ---------------------------------------------------------------------------
# Mock handlers
# ---------------------------------------------------------------------------


def _happy_handler(request: httpx.Request) -> httpx.Response:
    """Handles all standard Admin API reads + PUT upserts successfully."""
    path = request.url.path
    method = request.method

    if path == "/status":
        return httpx.Response(200, json=_STATUS_BODY)
    if path == "/services" and method == "GET":
        return httpx.Response(200, json=_SERVICES_BODY)
    if path == "/routes" and method == "GET":
        return httpx.Response(200, json=_ROUTES_BODY)
    if path == "/plugins" and method == "GET":
        return httpx.Response(200, json=_PLUGINS_BODY)
    if method == "PUT" and path.startswith("/services/"):
        # Accept any service or route upsert
        name = path.rstrip("/").split("/")[-1]
        return httpx.Response(200, json={"id": f"id-{name}", "name": name})

    return httpx.Response(404, json={"message": "not found"})


def _service_failure_handler(request: httpx.Request) -> httpx.Response:
    """Returns 409 for the first service upsert, success for all others."""
    path = request.url.path
    method = request.method

    if method == "PUT" and path == "/services/nutratenant-tenent":
        return httpx.Response(409, json={"message": "conflict"})
    return _happy_handler(request)


def _unreachable_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("Connection refused by mock")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(handler=_happy_handler) -> KongAdminService:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://kong-admin:8001",
    )
    return KongAdminService(http_client=client)


# ---------------------------------------------------------------------------
# Tests — read operations
# ---------------------------------------------------------------------------


async def test_get_status_returns_node_info() -> None:
    svc = _make_service()
    status = await svc.get_status()
    assert "server" in status
    assert status["server"]["connections_accepted"] == 100


async def test_list_services_returns_list() -> None:
    svc = _make_service()
    services = await svc.list_services()
    assert len(services) == 2
    names = {s["name"] for s in services}
    assert "nutratenant-tenent" in names
    assert "nutratenant-tenant-provisioning" in names


async def test_list_routes_returns_list() -> None:
    svc = _make_service()
    routes = await svc.list_routes()
    assert len(routes) == 2
    paths = [p for r in routes for p in r["paths"]]
    assert "/api/v1/tenants" in paths


async def test_list_plugins_returns_list() -> None:
    svc = _make_service()
    plugins = await svc.list_plugins()
    assert len(plugins) == 3
    names = {p["name"] for p in plugins}
    assert "cors" in names
    assert "prometheus" in names


# ---------------------------------------------------------------------------
# Tests — sync_routes
# ---------------------------------------------------------------------------


async def test_sync_routes_success() -> None:
    svc = _make_service()
    result = await svc.sync_routes()
    # 4 routes: /api/v1/tenants, /api/v1/lifecycle, /api/v1/isolation, /api/v1/provisioning
    assert len(result.synced) == 4
    assert len(result.failed) == 0
    assert len(result.skipped) == 0
    assert set(result.synced) == {
        "/api/v1/tenants",
        "/api/v1/lifecycle",
        "/api/v1/isolation",
        "/api/v1/provisioning",
    }


async def test_sync_routes_service_failure_marks_failed() -> None:
    svc = _make_service(_service_failure_handler)
    result = await svc.sync_routes()
    # The three tenent routes fail at service upsert; provisioning succeeds
    assert "/api/v1/tenants" in result.failed
    assert "/api/v1/lifecycle" in result.failed
    assert "/api/v1/isolation" in result.failed
    assert "/api/v1/provisioning" in result.synced


async def test_sync_routes_admin_unreachable_marks_failed() -> None:
    svc = _make_service(_unreachable_handler)
    result = await svc.sync_routes()
    assert len(result.failed) == 4
    assert len(result.synced) == 0


async def test_sync_routes_total_matches() -> None:
    svc = _make_service()
    result = await svc.sync_routes()
    assert result.total == len(result.synced) + len(result.skipped) + len(result.failed)
    assert result.total == 4


async def test_sync_result_is_kong_sync_result_instance() -> None:
    svc = _make_service()
    result = await svc.sync_routes()
    assert isinstance(result, KongSyncResult)


# ---------------------------------------------------------------------------
# Tests — error propagation for read endpoints
# ---------------------------------------------------------------------------


async def test_get_status_raises_on_http_error() -> None:
    def bad_handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "internal error"})

    svc = _make_service(bad_handler)
    with pytest.raises(httpx.HTTPStatusError):
        await svc.get_status()


async def test_list_services_raises_on_transport_error() -> None:
    svc = _make_service(_unreachable_handler)
    with pytest.raises(httpx.ConnectError):
        await svc.list_services()
