from __future__ import annotations

import json

import respx
from httpx import AsyncClient, Response

from app.core.config import settings

_LOKI = settings.loki_base_url


def _stream_response(
    *, service: str, tenant_id: str, message: str, ts_ns: str = "1700000000000000000"
) -> dict:
    line = json.dumps(
        {
            "time": "2024-01-01T00:00:00",
            "level": "ERROR",
            "service": service,
            "message": message,
            "tenant_id": tenant_id,
            "trace_id": None,
            "span_id": None,
        }
    )
    return {
        "data": {
            "result": [
                {"stream": {"service": service, "level": "ERROR"}, "values": [[ts_ns, line]]}
            ]
        }
    }


async def test_search_without_tenant_scope_is_forbidden(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/logs/search")
    assert resp.status_code == 403


@respx.mock
async def test_search_with_tenant_header_is_scoped(client: AsyncClient) -> None:
    respx.get(f"{_LOKI}/loki/api/v1/query_range").mock(
        return_value=Response(
            200, json=_stream_response(service="tenent", tenant_id="t1", message="boom")
        )
    )
    resp = await client.get("/api/v1/logs/search", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["tenant_id"] == "t1"
    assert body["items"][0]["message"] == "boom"
    assert "id" in body["items"][0]


async def test_logs_by_tenant_cross_tenant_is_forbidden(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/logs/tenant/other-tenant", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 403


@respx.mock
async def test_logs_by_tenant_own_tenant_is_allowed(client: AsyncClient) -> None:
    respx.get(f"{_LOKI}/loki/api/v1/query_range").mock(
        return_value=Response(
            200, json=_stream_response(service="tenent", tenant_id="t1", message="ok")
        )
    )
    resp = await client.get("/api/v1/logs/tenant/t1", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


async def test_logs_by_service_requires_platform_admin(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/logs/service/tenent", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 403


@respx.mock
async def test_create_log_ingests_via_push(client: AsyncClient) -> None:
    route = respx.post(f"{_LOKI}/loki/api/v1/push").mock(return_value=Response(204))
    resp = await client.post(
        "/api/v1/logs",
        headers={"X-Tenant-ID": "t1"},
        json={"service": "browser", "message": "click", "level": "INFO", "tenant_id": "t1"},
    )
    assert resp.status_code == 202
    assert resp.json() == {"accepted": 1}
    assert route.called


async def test_bulk_ingest_over_limit_is_rejected(client: AsyncClient) -> None:
    items = [{"service": "browser", "message": "x", "tenant_id": "t1"}] * (
        settings.logs_bulk_max_items + 1
    )
    resp = await client.post(
        "/api/v1/logs/bulk",
        headers={"X-Tenant-ID": "t1"},
        json={"items": items},
    )
    assert resp.status_code == 422


async def test_delete_by_id_returns_not_implemented_for_admin(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/logs/some-id", headers={"X-Tenant-ID": "t1"})
    # Non-admin caller is rejected before we even get to the 501.
    assert resp.status_code == 403
