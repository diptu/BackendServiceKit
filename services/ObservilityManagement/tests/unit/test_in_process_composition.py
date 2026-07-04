"""Proves the one real architectural change this merge makes — TODO.md
Decision #4 — actually works: a single respx-mocked Alertmanager response
is consumed by Alerting's own router *and*, in the same request cycle,
by Monitoring's and Observability's in-process calls into Alerting's
service class, with zero network hop between domains."""

from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.core.config import settings

_AM = settings.alertmanager_base_url
_GW = settings.api_gateway_base_url

_RAW_ALERT = {
    "fingerprint": "a1",
    "labels": {"alertname": "ServiceDown", "service": "tenent", "severity": "critical"},
    "annotations": {},
    "startsAt": "2024-01-01T00:00:00.000Z",
    "endsAt": "0001-01-01T00:00:00Z",
    "status": {"state": "active", "silencedBy": [], "inhibitedBy": []},
    "receivers": [],
}


@respx.mock
async def test_one_alert_is_visible_from_alerting_monitoring_and_observability(
    client: AsyncClient,
) -> None:
    respx.get(f"{_AM}/api/v2/alerts").mock(return_value=Response(200, json=[_RAW_ALERT]))
    respx.get(f"{_GW}/api/v1/gateway/status").mock(
        return_value=Response(200, json={"upstreams": []})
    )

    alerts_resp = await client.get("/api/v1/alerts")
    assert alerts_resp.json()["count"] == 1

    status_resp = await client.get("/api/v1/monitoring/status")
    assert status_resp.json()["active_alert_count"] == 1

    incidents_resp = await client.get("/api/v1/observability/incidents")
    incidents_body = incidents_resp.json()
    assert incidents_body["count"] == 1
    assert incidents_body["items"][0]["alertname"] == "ServiceDown"

    anomalies_resp = await client.get("/api/v1/observability/anomalies")
    anomalies_body = anomalies_resp.json()
    assert anomalies_body["count"] == 1
    assert anomalies_body["items"][0]["severity"] == "critical"

    dashboard_resp = await client.get("/api/v1/observability/dashboard")
    assert dashboard_resp.json()["active_alert_count"] == 1
