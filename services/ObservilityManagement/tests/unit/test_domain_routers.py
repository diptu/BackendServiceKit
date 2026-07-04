"""Basic end-to-end tests for each domain's own router through the real DI
stack (respx-mocked tier-1 backends)."""

from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.core.config import settings

_LOKI = settings.loki_base_url
_TEMPO = settings.tempo_base_url
_PROM = settings.prometheus_base_url
_AM = settings.alertmanager_base_url


@respx.mock
async def test_logs_search(client: AsyncClient) -> None:
    respx.get(f"{_LOKI}/loki/api/v1/query_range").mock(
        return_value=Response(200, json={"data": {"result": []}})
    )
    resp = await client.get("/api/v1/logs/search")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "count": 0}


@respx.mock
async def test_traces_search(client: AsyncClient) -> None:
    respx.get(f"{_TEMPO}/api/search").mock(return_value=Response(200, json={"traces": []}))
    resp = await client.get("/api/v1/traces/search")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "count": 0}


@respx.mock
async def test_metrics_system(client: AsyncClient) -> None:
    respx.get(f"{_PROM}/api/v1/query").mock(
        return_value=Response(
            200, json={"data": {"result": [{"metric": {"job": "tenent"}, "value": [1, "1"]}]}}
        )
    )
    resp = await client.get("/api/v1/metrics/system")
    assert resp.status_code == 200
    assert resp.json()["data"]["up"][0]["job"] == "tenent"


@respx.mock
async def test_monitoring_status(client: AsyncClient) -> None:
    respx.get(f"{settings.api_gateway_base_url}/api/v1/gateway/status").mock(
        return_value=Response(200, json={"upstreams": []})
    )
    respx.get(f"{_AM}/api/v2/alerts").mock(return_value=Response(200, json=[]))
    resp = await client.get("/api/v1/monitoring/status")
    assert resp.status_code == 200
    assert resp.json()["active_alert_count"] == 0


@respx.mock
async def test_alerts_list(client: AsyncClient) -> None:
    respx.get(f"{_AM}/api/v2/alerts").mock(return_value=Response(200, json=[]))
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "count": 0}


@respx.mock
async def test_health_dependencies(client: AsyncClient) -> None:
    respx.get(f"{settings.tenent_base_url}/health").mock(
        return_value=Response(200, json={"status": "ok"})
    )
    respx.get(f"{settings.tenent_base_url}/ready").mock(
        return_value=Response(200, json={"status": "ok"})
    )
    respx.get(f"{settings.api_gateway_base_url}/health").mock(
        return_value=Response(200, json={"status": "ok"})
    )
    respx.get(f"{settings.api_gateway_base_url}/ready").mock(
        return_value=Response(200, json={"status": "ok"})
    )
    resp = await client.get("/api/v1/health/dependencies")
    assert resp.status_code == 200
    body = resp.json()
    names = {s["name"] for s in body["services"]}
    assert names == {"tenent", "api-gateway", settings.app_name}
