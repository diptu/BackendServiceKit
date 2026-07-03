from __future__ import annotations

from typing import Any

from app.services.incident_service import IncidentService


class _FakeAlertingClient:
    def __init__(self, alerts: list[dict[str, Any]] | None) -> None:
        self._alerts = alerts

    async def list_alerts(self) -> list[dict[str, Any]] | None:
        return self._alerts


async def test_list_incidents_groups_active_alerts() -> None:
    alerts = [
        {
            "fingerprint": "a1",
            "state": "active",
            "labels": {"alertname": "ServiceDown", "service": "tenent"},
            "starts_at": "2024-01-01T00:00:00Z",
        }
    ]
    service = IncidentService(_FakeAlertingClient(alerts))  # type: ignore[arg-type]
    incidents = await service.list_incidents()
    assert len(incidents) == 1
    assert incidents[0].alertname == "ServiceDown"


async def test_list_incidents_empty_when_alerting_unreachable() -> None:
    service = IncidentService(_FakeAlertingClient(None))  # type: ignore[arg-type]
    assert await service.list_incidents() == []


async def test_list_incidents_empty_when_no_active_alerts() -> None:
    alerts = [{"fingerprint": "a1", "state": "suppressed", "labels": {"alertname": "X"}}]
    service = IncidentService(_FakeAlertingClient(alerts))  # type: ignore[arg-type]
    assert await service.list_incidents() == []
