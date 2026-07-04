"""Evidence-gathering engine for /root-cause and /correlation (TODO.md
Decision #7) — in-process, no HTTP hop. Gathers correlated evidence for a
service+time-window; does not compute a verdict."""

from __future__ import annotations

import asyncio

from app.domains.alerting.services.alert_service import AlertService
from app.domains.logging.services.log_query_service import LogQueryService
from app.domains.metrics.services.metrics_query_service import MetricsQueryService
from app.domains.observability.models import EvidenceItem
from app.domains.observability.services.safe_call import safe_call
from app.domains.tracing.services.trace_query_service import TraceQueryService


class CorrelationService:
    def __init__(
        self,
        log_service: LogQueryService,
        trace_service: TraceQueryService,
        metrics_service: MetricsQueryService,
        alert_service: AlertService,
    ) -> None:
        self._logs = log_service
        self._traces = trace_service
        self._metrics = metrics_service
        self._alerts = alert_service

    async def gather_evidence(self, *, service: str, minutes: float = 15.0) -> list[EvidenceItem]:
        log_entries, trace_summaries, metrics_body, alerts = await asyncio.gather(
            safe_call(self._logs.search(service=service, level="error", minutes=minutes)),
            safe_call(
                self._traces.search(query=f"service={service} status=error", minutes=minutes)
            ),
            safe_call(self._metrics.system_metrics()),
            safe_call(self._alerts.list_alerts()),
        )

        evidence: list[EvidenceItem] = []
        if log_entries:
            evidence.extend(
                EvidenceItem(
                    source="log", timestamp=e.timestamp, summary=e.line, raw={"labels": e.labels}
                )
                for e in log_entries
            )
        if trace_summaries:
            evidence.extend(
                EvidenceItem(
                    source="trace",
                    timestamp=s.start_time,
                    summary=s.root_name or s.trace_id,
                    raw={"trace_id": s.trace_id},
                )
                for s in trace_summaries
            )
        if alerts:
            evidence.extend(
                EvidenceItem(
                    source="alert",
                    timestamp=a.starts_at,
                    summary=a.labels.get("alertname", "unknown"),
                    raw={"fingerprint": a.fingerprint},
                )
                for a in alerts
                if a.labels.get("service") == service or a.labels.get("job") == service
            )
        if metrics_body:
            evidence.append(
                EvidenceItem(
                    source="metric",
                    timestamp="",
                    summary=f"Current system metrics snapshot for {service}",
                    raw=metrics_body,
                )
            )

        evidence.sort(key=lambda e: e.timestamp, reverse=True)
        return evidence

    async def root_cause_for_alert(
        self, *, fingerprint: str, minutes: float = 15.0
    ) -> list[EvidenceItem]:
        alerts = await safe_call(self._alerts.list_alerts())
        alert = next((a for a in (alerts or []) if a.fingerprint == fingerprint), None)
        if alert is None:
            return []

        service = alert.labels.get("service") or alert.labels.get("job") or ""
        if not service:
            return [
                EvidenceItem(
                    source="alert",
                    timestamp=alert.starts_at,
                    summary=alert.labels.get("alertname", "unknown"),
                    raw={"fingerprint": alert.fingerprint},
                )
            ]
        return await self.gather_evidence(service=service, minutes=minutes)
