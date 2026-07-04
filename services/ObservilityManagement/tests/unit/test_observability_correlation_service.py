from __future__ import annotations

from typing import Any

from app.domains.alerting.models import Alert
from app.domains.logging.repositories.log_repository import LogEntry
from app.domains.observability.services.correlation_service import CorrelationService
from app.domains.tracing.repositories.trace_repository import TraceSummary


class _FakeLog:
    def __init__(self, entries: list[LogEntry] | None) -> None:
        self._entries = entries

    async def search(self, **kwargs: Any) -> list[LogEntry]:
        return self._entries or []


class _FakeTrace:
    def __init__(self, summaries: list[TraceSummary] | None) -> None:
        self._summaries = summaries

    async def search(self, **kwargs: Any) -> list[TraceSummary]:
        return self._summaries or []


class _FakeMetrics:
    def __init__(self, body: dict[str, Any] | None) -> None:
        self._body = body

    async def system_metrics(self) -> dict[str, Any] | None:
        return self._body


class _FakeAlert:
    def __init__(self, alerts: list[Alert] | None) -> None:
        self._alerts = alerts

    async def list_alerts(self) -> list[Alert]:
        return self._alerts or []


def _alert(fingerprint: str, service: str, alertname: str = "X") -> Alert:
    return Alert(
        fingerprint=fingerprint,
        labels={"alertname": alertname, "service": service},
        annotations={},
        starts_at="2024-01-01T00:00:00Z",
        ends_at="",
        state="active",
    )


def _make_service(**overrides: Any) -> CorrelationService:
    return CorrelationService(
        overrides.get("logging", _FakeLog(None)),
        overrides.get("tracing", _FakeTrace(None)),
        overrides.get("metrics", _FakeMetrics(None)),
        overrides.get("alerting", _FakeAlert(None)),
    )  # type: ignore[arg-type]


async def test_gather_evidence_combines_all_sources() -> None:
    service = _make_service(
        logging=_FakeLog([LogEntry(timestamp="2024-01-01T00:00:01Z", line="db timeout")]),
        tracing=_FakeTrace(
            [
                TraceSummary(
                    trace_id="t1",
                    root_service="tenent",
                    root_name="x",
                    start_time="2024-01-01T00:00:02Z",
                    duration_ms=1,
                )
            ]
        ),
        metrics=_FakeMetrics({"data": {"cpu": 90}}),
        alerting=_FakeAlert([_alert("a1", "tenent", "HighCPU")]),
    )
    evidence = await service.gather_evidence(service="tenent")
    assert {e.source for e in evidence} == {"log", "trace", "metric", "alert"}


async def test_alert_evidence_filters_by_service_label() -> None:
    service = _make_service(
        alerting=_FakeAlert([_alert("a1", "tenent", "X"), _alert("a2", "alerting", "Y")])
    )
    evidence = await service.gather_evidence(service="tenent")
    alert_evidence = [e for e in evidence if e.source == "alert"]
    assert len(alert_evidence) == 1
    assert alert_evidence[0].summary == "X"


async def test_root_cause_for_alert_resolves_service_and_gathers() -> None:
    service = _make_service(
        alerting=_FakeAlert([_alert("abc123", "tenent", "ServiceDown")]),
        logging=_FakeLog([LogEntry(timestamp="2024-01-01T00:00:01Z", line="conn refused")]),
    )
    evidence = await service.root_cause_for_alert(fingerprint="abc123")
    assert any(e.source == "log" for e in evidence)
    assert any(e.source == "alert" and e.summary == "ServiceDown" for e in evidence)


async def test_root_cause_for_unknown_fingerprint_returns_empty() -> None:
    service = _make_service(alerting=_FakeAlert([]))
    evidence = await service.root_cause_for_alert(fingerprint="does-not-exist")
    assert evidence == []


async def test_root_cause_without_service_label_returns_alert_only() -> None:
    service = _make_service(
        alerting=_FakeAlert(
            [
                Alert(
                    fingerprint="abc123",
                    labels={"alertname": "GlobalThing"},
                    annotations={},
                    starts_at="2024-01-01T00:00:00Z",
                    ends_at="",
                    state="active",
                )
            ]
        )
    )
    evidence = await service.root_cause_for_alert(fingerprint="abc123")
    assert len(evidence) == 1
    assert evidence[0].source == "alert"
