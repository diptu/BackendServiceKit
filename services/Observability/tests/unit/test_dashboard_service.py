from __future__ import annotations

from typing import Any

from app.services.dashboard_service import DashboardService


class _FakeLoggingClient:
    def __init__(self, error_count: int | None = 3) -> None:
        self._error_count = error_count

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        return self._error_count


class _FakeTracingClient:
    def __init__(self, error_count: int | None = 1) -> None:
        self._error_count = error_count

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        return self._error_count


_UNSET = object()


class _FakeMetricsClient:
    def __init__(self, body: Any = _UNSET) -> None:
        self._body = {"data": {"cpu": 42}} if body is _UNSET else body

    async def system_metrics(self) -> dict[str, Any] | None:
        return self._body  # type: ignore[no-any-return]


class _FakeHealthClient:
    def __init__(self, body: Any = _UNSET) -> None:
        self._body = {"overall_status": "healthy"} if body is _UNSET else body

    async def dependencies(self) -> dict[str, Any] | None:
        return self._body  # type: ignore[no-any-return]


class _FakeAlertingClient:
    def __init__(self, alerts: Any = _UNSET) -> None:
        self._alerts = (
            [{"state": "active"}, {"state": "suppressed"}] if alerts is _UNSET else alerts
        )

    async def list_alerts(self) -> list[dict[str, Any]] | None:
        return self._alerts


def _make_service(**overrides: Any) -> DashboardService:
    return DashboardService(
        overrides.get("logging", _FakeLoggingClient()),
        overrides.get("tracing", _FakeTracingClient()),
        overrides.get("metrics", _FakeMetricsClient()),
        overrides.get("health", _FakeHealthClient()),
        overrides.get("alerting", _FakeAlertingClient()),
        window_minutes=15.0,
    )  # type: ignore[arg-type]


async def test_dashboard_composes_all_five_sources() -> None:
    service = _make_service()
    summary = await service.get_dashboard()
    assert summary.error_log_count == 3
    assert summary.error_trace_count == 1
    assert summary.headline_metrics == {"cpu": 42}
    assert summary.fleet_status == "healthy"
    assert summary.active_alert_count == 1  # only the "active" one counts


async def test_dashboard_degrades_when_a_source_is_unreachable() -> None:
    service = _make_service(logging=_FakeLoggingClient(error_count=None))
    summary = await service.get_dashboard()
    assert summary.error_log_count is None
    assert summary.error_trace_count == 1  # other sources unaffected


async def test_dashboard_handles_all_sources_unreachable() -> None:
    service = _make_service(
        logging=_FakeLoggingClient(error_count=None),
        tracing=_FakeTracingClient(error_count=None),
        metrics=_FakeMetricsClient(body=None),
        health=_FakeHealthClient(body=None),
        alerting=_FakeAlertingClient(alerts=None),
    )
    summary = await service.get_dashboard()
    assert summary.error_log_count is None
    assert summary.error_trace_count is None
    assert summary.headline_metrics == {}
    assert summary.fleet_status is None
    assert summary.active_alert_count is None
