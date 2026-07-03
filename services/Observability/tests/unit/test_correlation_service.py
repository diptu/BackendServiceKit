from __future__ import annotations

from typing import Any

from app.services.correlation_service import CorrelationService


class _FakeLoggingClient:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def search(self, *, query: str, minutes: float = 15.0) -> dict[str, Any] | None:
        return self._body


class _FakeTracingClient:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def search(self, *, query: str, minutes: float = 15.0) -> dict[str, Any] | None:
        return self._body


class _FakeMetricsClient:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def system_metrics(self) -> dict[str, Any] | None:
        return self._body


class _FakeAlertingClient:
    def __init__(self, alerts: list[dict[str, Any]] | None) -> None:
        self._alerts = alerts

    async def list_alerts(self) -> list[dict[str, Any]] | None:
        return self._alerts


def _make_service(**overrides: Any) -> CorrelationService:
    return CorrelationService(
        overrides.get("logging", _FakeLoggingClient(None)),
        overrides.get("tracing", _FakeTracingClient(None)),
        overrides.get("metrics", _FakeMetricsClient(None)),
        overrides.get("alerting", _FakeAlertingClient(None)),
    )  # type: ignore[arg-type]


async def test_gather_evidence_combines_all_sources() -> None:
    logging_body = {"items": [{"timestamp": "2024-01-01T00:00:01Z", "message": "db timeout"}]}
    tracing_body = {"items": [{"timestamp": "2024-01-01T00:00:02Z", "trace_id": "t1"}]}
    metrics_body = {"data": {"cpu": 90}}
    alerts = [
        {
            "fingerprint": "a1",
            "starts_at": "2024-01-01T00:00:00Z",
            "labels": {"alertname": "HighCPU", "service": "tenent"},
        }
    ]
    service = _make_service(
        logging=_FakeLoggingClient(logging_body),
        tracing=_FakeTracingClient(tracing_body),
        metrics=_FakeMetricsClient(metrics_body),
        alerting=_FakeAlertingClient(alerts),
    )

    evidence = await service.gather_evidence(service="tenent")
    sources = {e.source for e in evidence}
    assert sources == {"log", "trace", "metric", "alert"}


async def test_alert_evidence_filters_by_service_label() -> None:
    alerts = [
        {"fingerprint": "a1", "starts_at": "t", "labels": {"alertname": "X", "service": "tenent"}},
        {
            "fingerprint": "a2",
            "starts_at": "t",
            "labels": {"alertname": "Y", "service": "alerting"},
        },
    ]
    service = _make_service(alerting=_FakeAlertingClient(alerts))
    evidence = await service.gather_evidence(service="tenent")
    alert_evidence = [e for e in evidence if e.source == "alert"]
    assert len(alert_evidence) == 1
    assert alert_evidence[0].summary == "X"


async def test_root_cause_for_alert_resolves_service_and_gathers() -> None:
    alerts = [
        {
            "fingerprint": "abc123",
            "starts_at": "2024-01-01T00:00:00Z",
            "labels": {"alertname": "ServiceDown", "service": "tenent"},
        }
    ]
    logging_body = {"items": [{"timestamp": "2024-01-01T00:00:01Z", "message": "conn refused"}]}
    service = _make_service(
        alerting=_FakeAlertingClient(alerts), logging=_FakeLoggingClient(logging_body)
    )

    evidence = await service.root_cause_for_alert(fingerprint="abc123")
    assert any(e.source == "log" for e in evidence)
    assert any(e.source == "alert" and e.summary == "ServiceDown" for e in evidence)


async def test_root_cause_for_unknown_fingerprint_returns_empty() -> None:
    service = _make_service(alerting=_FakeAlertingClient([]))
    evidence = await service.root_cause_for_alert(fingerprint="does-not-exist")
    assert evidence == []


async def test_root_cause_for_alert_without_service_label_returns_alert_only() -> None:
    alerts = [
        {
            "fingerprint": "abc123",
            "starts_at": "2024-01-01T00:00:00Z",
            "labels": {"alertname": "GlobalThing"},
        }
    ]
    service = _make_service(alerting=_FakeAlertingClient(alerts))
    evidence = await service.root_cause_for_alert(fingerprint="abc123")
    assert len(evidence) == 1
    assert evidence[0].source == "alert"
    assert evidence[0].summary == "GlobalThing"
