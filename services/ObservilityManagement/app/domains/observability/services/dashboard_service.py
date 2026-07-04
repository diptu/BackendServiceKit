"""Composes five domains' existing summary-shaped calls into one payload —
in-process, no HTTP hop (TODO.md Decision #4). Computes nothing new itself."""

from __future__ import annotations

import asyncio

from app.domains.alerting.services.alert_service import AlertService
from app.domains.health.services.health_service import HealthService
from app.domains.logging.services.log_query_service import LogQueryService
from app.domains.metrics.services.metrics_query_service import MetricsQueryService
from app.domains.observability.models import DashboardSummary
from app.domains.observability.services.safe_call import safe_call
from app.domains.tracing.services.trace_query_service import TraceQueryService


class DashboardService:
    def __init__(
        self,
        log_service: LogQueryService,
        trace_service: TraceQueryService,
        metrics_service: MetricsQueryService,
        health_service: HealthService,
        alert_service: AlertService,
        *,
        window_minutes: float,
    ) -> None:
        self._logs = log_service
        self._traces = trace_service
        self._metrics = metrics_service
        self._health = health_service
        self._alerts = alert_service
        self._window_minutes = window_minutes

    async def get_dashboard(self) -> DashboardSummary:
        error_logs, error_traces, metrics_body, fleet, alerts = await asyncio.gather(
            safe_call(self._logs.count_errors(minutes=self._window_minutes)),
            safe_call(self._traces.count_errors(minutes=self._window_minutes)),
            safe_call(self._metrics.system_metrics()),
            safe_call(self._health.get_fleet_health()),
            safe_call(self._alerts.list_alerts()),
        )

        fleet_status = fleet.overall_status if fleet else None
        active_alert_count = (
            sum(1 for a in alerts if a.state == "active") if alerts is not None else None
        )
        headline_metrics = metrics_body.get("data", {}) if metrics_body else {}

        return DashboardSummary(
            error_log_count=error_logs,
            error_trace_count=error_traces,
            headline_metrics=headline_metrics,
            fleet_status=fleet_status,
            active_alert_count=active_alert_count,
        )
