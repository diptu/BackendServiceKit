from __future__ import annotations

from app.domains.alerting.models import Alert
from app.domains.observability.services.incident_service import IncidentService


class _FakeAlert:
    def __init__(self, alerts: list[Alert] | None, *, raise_error: bool = False) -> None:
        self._alerts = alerts
        self._raise_error = raise_error

    async def list_alerts(self) -> list[Alert]:
        if self._raise_error:
            raise RuntimeError("boom")
        return self._alerts or []


def _alert() -> Alert:
    return Alert(
        fingerprint="a1",
        labels={"alertname": "ServiceDown", "service": "tenent"},
        annotations={},
        starts_at="2024-01-01T00:00:00Z",
        ends_at="",
        state="active",
    )


async def test_list_incidents_groups_active_alerts() -> None:
    service = IncidentService(_FakeAlert([_alert()]))  # type: ignore[arg-type]
    incidents = await service.list_incidents()
    assert len(incidents) == 1
    assert incidents[0].alertname == "ServiceDown"


async def test_list_incidents_empty_when_alerting_raises() -> None:
    service = IncidentService(_FakeAlert(None, raise_error=True))  # type: ignore[arg-type]
    assert await service.list_incidents() == []
