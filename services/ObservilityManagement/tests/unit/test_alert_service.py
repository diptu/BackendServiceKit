from __future__ import annotations

from typing import Any

import pytest

from app.domains.alerting.exceptions import AlertNotFoundError
from app.domains.alerting.services.alert_service import AlertService

_RAW_ALERT: dict[str, Any] = {
    "fingerprint": "abc123",
    "labels": {"alertname": "Test", "severity": "warning"},
    "annotations": {"summary": "test"},
    "startsAt": "2024-01-01T00:00:00.000Z",
    "endsAt": "0001-01-01T00:00:00Z",
    "status": {"state": "active", "silencedBy": [], "inhibitedBy": []},
    "receivers": [{"name": "default-receiver"}],
}


class _FakeAlertmanagerClient:
    def __init__(self, alerts: list[dict[str, Any]] | None = None) -> None:
        self._alerts = alerts if alerts is not None else [_RAW_ALERT]
        self.posted: list[dict[str, Any]] = []
        self.silences: list[dict[str, Any]] = []

    async def list_alerts(self) -> list[dict[str, Any]]:
        return self._alerts

    async def post_alerts(self, alerts: list[dict[str, Any]]) -> None:
        self.posted.extend(alerts)

    async def create_silence(self, *, silence: dict[str, Any]) -> str:
        self.silences.append(silence)
        return "fake-silence-id"


def _make_service(
    alerts: list[dict[str, Any]] | None = None,
) -> tuple[AlertService, _FakeAlertmanagerClient]:
    fake = _FakeAlertmanagerClient(alerts)
    return AlertService(fake, default_ack_minutes=240), fake  # type: ignore[arg-type]


async def test_list_alerts_parses_raw_alerts() -> None:
    service, _ = _make_service()
    alerts = await service.list_alerts()
    assert len(alerts) == 1
    assert alerts[0].fingerprint == "abc123"


async def test_get_alert_not_found_raises() -> None:
    service, _ = _make_service(alerts=[])
    with pytest.raises(AlertNotFoundError):
        await service.get_alert("does-not-exist")


async def test_acknowledge_creates_silence_matching_alert_labels() -> None:
    service, fake = _make_service()
    silence_id = await service.acknowledge("abc123", comment="ack it")
    assert silence_id == "fake-silence-id"
    matcher_names = {m["name"] for m in fake.silences[0]["matchers"]}
    assert matcher_names == {"alertname", "severity"}


async def test_resolve_reposts_alert_with_ends_at_set() -> None:
    service, fake = _make_service()
    await service.resolve("abc123")
    posted = fake.posted[0]
    assert posted["endsAt"] != "0001-01-01T00:00:00Z"


async def test_send_test_alert_is_short_lived() -> None:
    service, fake = _make_service()
    result = await service.send_test_alert()
    assert result["labels"]["alertname"] == "AlertingDomainTestAlert"
    assert "endsAt" in fake.posted[0]
