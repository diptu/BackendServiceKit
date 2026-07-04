"""Simple, rule-based anomaly signals (TODO.md Decision #8) — in-process,
no HTTP hop. v1 surfaces one real, already-computed signal: currently-
firing critical-severity alerts. Not statistical/ML anomaly detection."""

from __future__ import annotations

from app.domains.alerting.services.alert_service import AlertService
from app.domains.observability.models import AnomalySignal
from app.domains.observability.services.safe_call import safe_call


class AnomalyService:
    def __init__(self, alert_service: AlertService) -> None:
        self._alerts = alert_service

    async def list_anomalies(self) -> list[AnomalySignal]:
        alerts = await safe_call(self._alerts.list_alerts())
        if not alerts:
            return []

        signals: list[AnomalySignal] = []
        for alert in alerts:
            if alert.state != "active" or alert.labels.get("severity") != "critical":
                continue
            alertname = alert.labels.get("alertname", "unknown")
            signals.append(
                AnomalySignal(
                    source="alert",
                    description=f"Critical alert firing: {alertname}",
                    severity="critical",
                )
            )
        return signals
