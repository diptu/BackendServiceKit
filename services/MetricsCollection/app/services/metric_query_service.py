"""Read-path business logic: turns validated filters into Prometheus queries."""

from __future__ import annotations

from app.domain.metric import MetricSample, MetricSeries
from app.infrastructure.prometheus.prometheus_client import PrometheusClient
from app.repositories.metric_repository import (
    build_promql,
    build_topk_promql,
    parse_query_result,
    parse_range_result,
)


class MetricQueryService:
    def __init__(self, prometheus_client: PrometheusClient) -> None:
        self._prom = prometheus_client

    async def list_metric_names(self) -> list[str]:
        return await self._prom.metric_names()

    async def query(
        self,
        *,
        metric: str,
        job: str | None = None,
        tenant_id: str | None = None,
        query_text: str | None = None,
        time_s: int | None = None,
    ) -> list[MetricSample]:
        promql = build_promql(metric=metric, job=job, tenant_id=tenant_id, query_text=query_text)
        data = await self._prom.instant_query(promql=promql, time_s=time_s)
        return parse_query_result(data)

    async def history(
        self,
        *,
        metric: str,
        job: str | None = None,
        tenant_id: str | None = None,
        query_text: str | None = None,
        start_s: int,
        end_s: int,
        step: str = "60s",
    ) -> list[MetricSeries]:
        promql = build_promql(metric=metric, job=job, tenant_id=tenant_id, query_text=query_text)
        data = await self._prom.range_query(promql=promql, start_s=start_s, end_s=end_s, step=step)
        return parse_range_result(data)

    async def top(
        self, *, metric: str, n: int, job: str | None = None, time_s: int | None = None
    ) -> list[MetricSample]:
        promql = build_topk_promql(metric=metric, n=n, job=job)
        data = await self._prom.instant_query(promql=promql, time_s=time_s)
        return parse_query_result(data)
