from __future__ import annotations

from typing import Any

from app.domains.alerting.models import Alert
from app.domains.health.models import FleetHealth
from app.domains.observability.services.dashboard_service import DashboardService

_UNSET = object()


class _FakeLog:
    def __init__(self, error_count: Any = 3) -> None:
        self._n = error_count

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        return self._n


class _FakeTrace:
    def __init__(self, error_count: Any = 1) -> None:
        self._n = error_count

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        return self._n


class _FakeMetrics:
    def __init__(self, body: Any = _UNSET) -> None:
        self._body = {"data": {"cpu": 42}} if body is _UNSET else body

    async def system_metrics(self) -> dict[str, Any] | None:
        return self._body


class _FakeHealth:
    def __init__(self, fleet: Any = _UNSET) -> None:
        self._fleet = FleetHealth(overall_status="healthy") if fleet is _UNSET else fleet

    async def get_fleet_health(self) -> FleetHealth | None:
        return self._fleet


class _FakeAlert:
    def __init__(self, alerts: Any = _UNSET, *, raise_error: bool = False) -> None:
        self._alerts = [_alert("active"), _alert("suppressed")] if alerts is _UNSET else alerts
        self._raise_error = raise_error

    async def list_alerts(self) -> list[Alert]:
        if self._raise_error:
            raise RuntimeError("boom")
        return self._alerts


def _alert(state: str) -> Alert:
    return Alert(fingerprint="a1", labels={}, annotations={}, starts_at="", ends_at="", state=state)


def _make_service(**overrides: Any) -> DashboardService:
    return DashboardService(
        overrides.get("logging", _FakeLog()),
        overrides.get("tracing", _FakeTrace()),
        overrides.get("metrics", _FakeMetrics()),
        overrides.get("health", _FakeHealth()),
        overrides.get("alerting", _FakeAlert()),
        window_minutes=15.0,
    )  # type: ignore[arg-type]


async def test_dashboard_composes_all_five_sources() -> None:
    service = _make_service()
    summary = await service.get_dashboard()
    assert summary.error_log_count == 3
    assert summary.error_trace_count == 1
    assert summary.headline_metrics == {"cpu": 42}
    assert summary.fleet_status == "healthy"
    assert summary.active_alert_count == 1


async def test_dashboard_degrades_when_alerting_raises() -> None:
    service = _make_service(alerting=_FakeAlert(raise_error=True))
    summary = await service.get_dashboard()
    assert summary.active_alert_count is None
    assert summary.error_log_count == 3  # other sources unaffected


async def test_dashboard_handles_all_sources_unreachable() -> None:
    service = _make_service(
        logging=_FakeLog(error_count=None),
        tracing=_FakeTrace(error_count=None),
        metrics=_FakeMetrics(body=None),
        health=_FakeHealth(fleet=None),
        alerting=_FakeAlert(alerts=None),
    )
    summary = await service.get_dashboard()
    assert summary.error_log_count is None
    assert summary.error_trace_count is None
    assert summary.headline_metrics == {}
    assert summary.fleet_status is None
    assert summary.active_alert_count is None
