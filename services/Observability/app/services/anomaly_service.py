"""Simple, rule-based anomaly signals — TODO.md Decision #8.

v1 surfaces one real, already-computed signal: currently-firing
critical-severity alerts. The metric-deviation-from-baseline heuristic
Decision #8 also describes is deferred — it needs MetricsCollection's
real time-range query API nailed down first (that service isn't currently
on disk to verify against; see this service's TODO.md Phase 0), and
shipping a guessed version of it would risk exactly the kind of fabricated
capability this service's design explicitly avoids elsewhere. Not a
statistical/ML anomaly-detection engine either way.
"""

from __future__ import annotations

from app.domain.observability import AnomalySignal
from app.infrastructure.siblings.alerting_client import AlertingClient


class AnomalyService:
    def __init__(self, alerting_client: AlertingClient) -> None:
        self._alerting = alerting_client

    async def list_anomalies(self) -> list[AnomalySignal]:
        raw_alerts = await self._alerting.list_alerts()
        if not raw_alerts:
            return []

        signals: list[AnomalySignal] = []
        for alert in raw_alerts:
            if not isinstance(alert, dict) or alert.get("state") != "active":
                continue
            labels = alert.get("labels") or {}
            if labels.get("severity") != "critical":
                continue
            alertname = labels.get("alertname", "unknown")
            signals.append(
                AnomalySignal(
                    source="alert",
                    description=f"Critical alert firing: {alertname}",
                    severity="critical",
                )
            )
        return signals
