from __future__ import annotations

from typing import Any

from app.services.anomaly_service import AnomalyService


class _FakeAlertingClient:
    def __init__(self, alerts: list[dict[str, Any]] | None) -> None:
        self._alerts = alerts

    async def list_alerts(self) -> list[dict[str, Any]] | None:
        return self._alerts


async def test_critical_active_alert_becomes_anomaly_signal() -> None:
    alerts = [
        {"state": "active", "labels": {"alertname": "ServiceDown", "severity": "critical"}},
        {"state": "active", "labels": {"alertname": "HighLatency", "severity": "warning"}},
        {"state": "suppressed", "labels": {"alertname": "PostgresDown", "severity": "critical"}},
    ]
    service = AnomalyService(_FakeAlertingClient(alerts))  # type: ignore[arg-type]
    signals = await service.list_anomalies()
    assert len(signals) == 1
    assert "ServiceDown" in signals[0].description
    assert signals[0].severity == "critical"


async def test_no_signals_when_alerting_unreachable() -> None:
    service = AnomalyService(_FakeAlertingClient(None))  # type: ignore[arg-type]
    assert await service.list_anomalies() == []


async def test_no_signals_when_no_critical_active_alerts() -> None:
    alerts = [{"state": "active", "labels": {"alertname": "X", "severity": "warning"}}]
    service = AnomalyService(_FakeAlertingClient(alerts))  # type: ignore[arg-type]
    assert await service.list_anomalies() == []
