from __future__ import annotations

from app.domains.alerting.models import Alert
from app.domains.observability.services.anomaly_service import AnomalyService


class _FakeAlert:
    def __init__(self, alerts: list[Alert] | None) -> None:
        self._alerts = alerts

    async def list_alerts(self) -> list[Alert]:
        return self._alerts or []


def _alert(*, state: str, severity: str) -> Alert:
    return Alert(
        fingerprint="a1",
        labels={"alertname": "ServiceDown", "severity": severity},
        annotations={},
        starts_at="",
        ends_at="",
        state=state,
    )


async def test_critical_active_alert_becomes_anomaly_signal() -> None:
    alerts = [
        _alert(state="active", severity="critical"),
        _alert(state="active", severity="warning"),
        _alert(state="suppressed", severity="critical"),
    ]
    service = AnomalyService(_FakeAlert(alerts))  # type: ignore[arg-type]
    signals = await service.list_anomalies()
    assert len(signals) == 1
    assert signals[0].severity == "critical"


async def test_no_signals_when_no_alerts() -> None:
    service = AnomalyService(_FakeAlert(None))  # type: ignore[arg-type]
    assert await service.list_anomalies() == []
