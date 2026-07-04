"""Business logic for the Metrics domain — composes PrometheusClient +
PushgatewayClient + metrics_repository. This is the plain service class
the Observability domain imports directly in-process (TODO.md Decision #4).

`system_metrics()` queries only `up` — no node-exporter is deployed
anywhere in this stack, same documented gap the original MetricsCollection
service's design carried; it is not invented here.
"""

from __future__ import annotations

from typing import Any

from app.domains.metrics.infrastructure.prometheus_client import PrometheusClient
from app.domains.metrics.infrastructure.pushgateway_client import PushgatewayClient
from app.domains.metrics.repositories.metrics_repository import (
    MetricSample,
    parse_instant_query_response,
)


class MetricsQueryService:
    def __init__(
        self, prometheus_client: PrometheusClient, pushgateway_client: PushgatewayClient
    ) -> None:
        self._prometheus = prometheus_client
        self._pushgateway = pushgateway_client

    async def query(self, *, promql: str) -> list[MetricSample]:
        raw = await self._prometheus.instant_query(query=promql)
        if raw is None:
            return []
        return parse_instant_query_response(raw)

    async def system_metrics(self) -> dict[str, Any] | None:
        raw = await self._prometheus.instant_query(query="up")
        if raw is None:
            return None
        samples = parse_instant_query_response(raw)
        return {"up": [{"job": s.metric.get("job", "unknown"), "value": s.value} for s in samples]}

    async def push(
        self, *, job: str, metric_name: str, value: float, labels: dict[str, str] | None = None
    ) -> bool:
        return await self._pushgateway.push_metric(
            job=job, metric_name=metric_name, value=value, labels=labels
        )
