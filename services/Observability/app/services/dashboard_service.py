"""Composes five services' existing summary-shaped endpoints — TODO.md
Decision #4. Computes nothing new itself."""

from __future__ import annotations

import asyncio

from app.domain.observability import DashboardSummary
from app.infrastructure.siblings.alerting_client import AlertingClient
from app.infrastructure.siblings.health_client import HealthClient
from app.infrastructure.siblings.logging_client import LoggingClient
from app.infrastructure.siblings.metrics_client import MetricsClient
from app.infrastructure.siblings.tracing_client import TracingClient


class DashboardService:
    def __init__(
        self,
        logging_client: LoggingClient,
        tracing_client: TracingClient,
        metrics_client: MetricsClient,
        health_client: HealthClient,
        alerting_client: AlertingClient,
        *,
        window_minutes: float,
    ) -> None:
        self._logging = logging_client
        self._tracing = tracing_client
        self._metrics = metrics_client
        self._health = health_client
        self._alerting = alerting_client
        self._window_minutes = window_minutes

    async def get_dashboard(self) -> DashboardSummary:
        error_logs, error_traces, metrics_body, health_body, raw_alerts = await asyncio.gather(
            self._logging.count_errors(minutes=self._window_minutes),
            self._tracing.count_errors(minutes=self._window_minutes),
            self._metrics.system_metrics(),
            self._health.dependencies(),
            self._alerting.list_alerts(),
        )

        fleet_status = health_body.get("overall_status") if health_body else None
        active_alert_count = None
        if raw_alerts is not None:
            active_alert_count = sum(
                1 for a in raw_alerts if isinstance(a, dict) and a.get("state") == "active"
            )
        headline_metrics = metrics_body.get("data", {}) if metrics_body else {}

        return DashboardSummary(
            error_log_count=error_logs,
            error_trace_count=error_traces,
            headline_metrics=headline_metrics,
            fleet_status=fleet_status,
            active_alert_count=active_alert_count,
        )
