"""End-to-end tests through the real DI stack (respx-mocked sibling
services) — proves the wiring in dependencies.py works, not just the
service layer in isolation (see the per-service test files for that)."""

from __future__ import annotations

import httpx
import respx
from httpx import AsyncClient, Response

from app.core.config import settings

_LOG = settings.logging_base_url
_TRACE = settings.distributed_tracing_base_url
_METRICS = settings.metrics_collection_base_url
_MON = settings.monitoring_base_url
_ALERT = settings.alerting_base_url
_HEALTH = settings.health_check_base_url

_ALERTS_BODY = {
    "items": [
        {
            "fingerprint": "a1",
            "state": "active",
            "labels": {"alertname": "ServiceDown", "service": "tenent", "severity": "critical"},
            "starts_at": "2024-01-01T00:00:00Z",
        }
    ],
    "count": 1,
}

_TRACES_BODY = {
    "items": [
        {
            "spans": [
                {"span_id": "1", "parent_span_id": None, "service_name": "api-gateway"},
                {"span_id": "2", "parent_span_id": "1", "service_name": "tenent"},
            ]
        }
    ],
    "count": 1,
}


def _mock_all(*, alerts: dict | None = None, traces: dict | None = None) -> None:
    respx.get(f"{_LOG}/api/v1/logs/search").mock(return_value=Response(200, json={"items": []}))
    respx.get(f"{_TRACE}/api/v1/traces/search").mock(
        return_value=Response(200, json=traces if traces is not None else _TRACES_BODY)
    )
    respx.get(f"{_METRICS}/api/v1/metrics/system").mock(
        return_value=Response(200, json={"data": {"cpu": 10}})
    )
    respx.get(f"{_MON}/api/v1/monitoring/summary").mock(return_value=Response(200, json={}))
    respx.get(f"{_ALERT}/api/v1/alerts").mock(
        return_value=Response(200, json=alerts if alerts is not None else _ALERTS_BODY)
    )
    respx.get(f"{_HEALTH}/api/v1/health/dependencies").mock(
        return_value=Response(200, json={"overall_status": "healthy"})
    )
    respx.get(f"{_HEALTH}/api/v1/health/live").mock(
        return_value=Response(200, json={"items": [{"service": "tenent", "reachable": True}]})
    )


@respx.mock
async def test_get_dashboard(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/dashboard")
    assert resp.status_code == 200
    assert resp.json()["fleet_status"] == "healthy"


@respx.mock
async def test_get_search(client: AsyncClient) -> None:
    _mock_all(traces={"items": []})
    resp = await client.get("/api/v1/observability/search", params={"q": "error"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@respx.mock
async def test_get_incidents(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/incidents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["alertname"] == "ServiceDown"


@respx.mock
async def test_get_dependencies(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/dependencies")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["edges"]) == 1
    assert body["edges"][0] == {"caller": "api-gateway", "callee": "tenent", "call_count": 1}


@respx.mock
async def test_get_topology_overlays_health(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/topology")
    assert resp.status_code == 200
    body = resp.json()
    tenent_node = next(n for n in body["nodes"] if n["name"] == "tenent")
    assert tenent_node["reachable"] is True


@respx.mock
async def test_get_anomalies(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/anomalies")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["items"][0]["severity"] == "critical"


@respx.mock
async def test_get_root_cause(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/root-cause", params={"alert_id": "a1"})
    assert resp.status_code == 200
    body = resp.json()
    assert any(item["source"] == "alert" for item in body["items"])


@respx.mock
async def test_get_root_cause_unknown_fingerprint_returns_empty(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/root-cause", params={"alert_id": "nope"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@respx.mock
async def test_get_correlation(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/correlation", params={"service": "tenent"})
    assert resp.status_code == 200
    body = resp.json()
    assert any(item["source"] == "alert" for item in body["items"])


@respx.mock
async def test_get_report(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.get("/api/v1/observability/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["incident_count"] == 1
    assert body["anomaly_count"] == 1
    assert body["dashboard"]["fleet_status"] == "healthy"


@respx.mock
async def test_export_dashboard_as_json(client: AsyncClient) -> None:
    _mock_all()
    resp = await client.post(
        "/api/v1/observability/export", json={"kind": "dashboard", "format": "json"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "dashboard"
    assert '"fleet_status"' in body["content"]


@respx.mock
async def test_export_search_as_csv(client: AsyncClient) -> None:
    _mock_all(traces=_TRACES_BODY)
    respx.get(f"{_TRACE}/api/v1/traces/search").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "trace_id": "t1",
                        "root_service": "tenent",
                    }
                ]
            },
        )
    )
    resp = await client.post(
        "/api/v1/observability/export",
        json={"kind": "search", "format": "csv", "query": "error"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["format"] == "csv"
    assert "source" in body["content"]


@respx.mock
async def test_one_dead_sibling_degrades_dashboard_not_crash(client: AsyncClient) -> None:
    _mock_all()
    respx.get(f"{_LOG}/api/v1/logs/search").mock(side_effect=httpx.ConnectError("boom"))
    resp = await client.get("/api/v1/observability/dashboard")
    assert resp.status_code == 200
    assert resp.json()["error_log_count"] is None
