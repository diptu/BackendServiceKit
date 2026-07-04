"""Tests the Monitoring domain's in-process call into Alerting's
AlertService (TODO.md Decision #4 applied within tier-3)."""

from __future__ import annotations

from typing import Any

from app.domains.alerting.models import Alert
from app.domains.monitoring.services.monitoring_service import MonitoringService


class _FakeGatewayClient:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def get_gateway_status(self) -> dict[str, Any] | None:
        return self._body


class _FakeTenentClient:
    def __init__(
        self, ready: dict[str, Any] | None = None, tenants: dict[str, Any] | None = None
    ) -> None:
        self._ready = ready
        self._tenants = tenants

    async def get_ready(self) -> dict[str, Any] | None:
        return self._ready

    async def list_tenants(self) -> dict[str, Any] | None:
        return self._tenants


class _FakeAlertService:
    def __init__(self, alerts: list[Alert] | None = None, *, raise_error: bool = False) -> None:
        self._alerts = alerts
        self._raise_error = raise_error

    async def list_alerts(self) -> list[Alert]:
        if self._raise_error:
            raise RuntimeError("Alertmanager down")
        return self._alerts or []


def _alert(state: str = "active") -> Alert:
    return Alert(
        fingerprint="a1",
        labels={"alertname": "X"},
        annotations={},
        starts_at="2024-01-01T00:00:00Z",
        ends_at="",
        state=state,
    )


async def test_get_status_counts_active_alerts() -> None:
    gateway_body = {"upstreams": [{"name": "tenent", "base_url": "u", "reachable": True}]}
    service = MonitoringService(
        _FakeGatewayClient(gateway_body),  # type: ignore[arg-type]
        _FakeTenentClient(),  # type: ignore[arg-type]
        _FakeAlertService([_alert("active"), _alert("suppressed")]),  # type: ignore[arg-type]
    )
    status = await service.get_status()
    assert status.active_alert_count == 1
    assert status.overall_status == "healthy"


async def test_get_status_degrades_alert_count_when_alerting_raises() -> None:
    """A genuine bug/exception from Alerting's in-process service must not
    crash Monitoring's whole /status response — TODO.md Decision #4."""
    service = MonitoringService(
        _FakeGatewayClient({"upstreams": []}),  # type: ignore[arg-type]
        _FakeTenentClient(),  # type: ignore[arg-type]
        _FakeAlertService(raise_error=True),  # type: ignore[arg-type]
    )
    status = await service.get_status()
    assert status.active_alert_count is None


async def test_get_resources_prefers_tenent_signal_over_gateway_fallback() -> None:
    ready_body = {"status": "ok", "dependencies": [{"name": "redis", "status": "up"}]}
    gateway_body = {"redis_connected": False, "rabbitmq_connected": True}
    service = MonitoringService(
        _FakeGatewayClient(gateway_body),  # type: ignore[arg-type]
        _FakeTenentClient(ready=ready_body),  # type: ignore[arg-type]
        _FakeAlertService([]),  # type: ignore[arg-type]
    )
    resources = await service.get_resources()
    assert resources.redis_reachable is True  # Tenent's real signal wins
    assert resources.rabbitmq_reachable is True


async def test_get_tenants_summarizes_by_status() -> None:
    tenants_body = {
        "items": [{"status": "active"}, {"status": "active"}, {"status": "suspended"}],
        "total": 3,
    }
    service = MonitoringService(
        _FakeGatewayClient(None),  # type: ignore[arg-type]
        _FakeTenentClient(tenants=tenants_body),  # type: ignore[arg-type]
        _FakeAlertService([]),  # type: ignore[arg-type]
    )
    summary = await service.get_tenants()
    assert summary.total == 3
    assert summary.by_status == {"active": 2, "suspended": 1}
