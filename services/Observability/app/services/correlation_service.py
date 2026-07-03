"""Evidence-gathering engine for /root-cause and /correlation — TODO.md
Decision #7. Gathers correlated evidence for a service+time-window; it
does not compute a verdict. Root-cause pre-fills the window from a
specific alert's own labels/timing; correlation takes an explicit
service+window from the caller — both call the same underlying gather.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.domain.observability import EvidenceItem
from app.infrastructure.siblings.alerting_client import AlertingClient
from app.infrastructure.siblings.logging_client import LoggingClient
from app.infrastructure.siblings.metrics_client import MetricsClient
from app.infrastructure.siblings.tracing_client import TracingClient


class CorrelationService:
    def __init__(
        self,
        logging_client: LoggingClient,
        tracing_client: TracingClient,
        metrics_client: MetricsClient,
        alerting_client: AlertingClient,
    ) -> None:
        self._logging = logging_client
        self._tracing = tracing_client
        self._metrics = metrics_client
        self._alerting = alerting_client

    async def gather_evidence(self, *, service: str, minutes: float = 15.0) -> list[EvidenceItem]:
        log_body, trace_body, metrics_body, raw_alerts = await asyncio.gather(
            self._logging.search(query=f'{{service="{service}", level="error"}}', minutes=minutes),
            self._tracing.search(query=f"service={service} status=error", minutes=minutes),
            self._metrics.system_metrics(),
            self._alerting.list_alerts(),
        )

        evidence: list[EvidenceItem] = []
        evidence.extend(_log_evidence(log_body))
        evidence.extend(_trace_evidence(trace_body))
        evidence.extend(_alert_evidence(raw_alerts, service))
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
        raw_alerts = await self._alerting.list_alerts()
        alert = next(
            (
                a
                for a in (raw_alerts or [])
                if isinstance(a, dict) and a.get("fingerprint") == fingerprint
            ),
            None,
        )
        if alert is None:
            return []

        labels = alert.get("labels") or {}
        service = str(labels.get("service") or labels.get("job") or "")
        if not service:
            return [
                EvidenceItem(
                    source="alert",
                    timestamp=str(alert.get("starts_at", "")),
                    summary=str(labels.get("alertname", "unknown")),
                    raw=alert,
                )
            ]
        return await self.gather_evidence(service=service, minutes=minutes)


def _log_evidence(body: dict[str, Any] | None) -> list[EvidenceItem]:
    if not body:
        return []
    items = body.get("items") or body.get("entries") or []
    if not isinstance(items, list):
        return []
    return [
        EvidenceItem(
            source="log",
            timestamp=str(item.get("timestamp", "")),
            summary=str(item.get("message") or item.get("line") or ""),
            raw=item,
        )
        for item in items
        if isinstance(item, dict)
    ]


def _trace_evidence(body: dict[str, Any] | None) -> list[EvidenceItem]:
    if not body:
        return []
    items = body.get("items") or body.get("traces") or []
    if not isinstance(items, list):
        return []
    return [
        EvidenceItem(
            source="trace",
            timestamp=str(item.get("timestamp") or item.get("start_time") or ""),
            summary=str(item.get("root_service") or item.get("trace_id") or ""),
            raw=item,
        )
        for item in items
        if isinstance(item, dict)
    ]


def _alert_evidence(raw_alerts: list[dict[str, Any]] | None, service: str) -> list[EvidenceItem]:
    if not raw_alerts:
        return []
    results = []
    for alert in raw_alerts:
        if not isinstance(alert, dict):
            continue
        labels = alert.get("labels") or {}
        if labels.get("service") != service and labels.get("job") != service:
            continue
        results.append(
            EvidenceItem(
                source="alert",
                timestamp=str(alert.get("starts_at", "")),
                summary=str(labels.get("alertname", "unknown")),
                raw=alert,
            )
        )
    return results
