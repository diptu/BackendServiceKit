"""Translates domain-level filters into PromQL and parses Prometheus's response back.

This is the only place PromQL syntax is constructed — no other module
should build a query string by hand (same rule Logging/DistributedTracing
apply to LogQL/TraceQL).

Prometheus's HTTP API returns a different `data.resultType` depending on the
query shape:
  - Instant query (`/api/v1/query`) → `vector` (list of `{metric, value:
    [ts, "val"]}`) or `scalar` (a bare `[ts, "val"]`, no labels at all).
  - Range query (`/api/v1/query_range`) → `matrix` (list of `{metric,
    values: [[ts, "val"], ...]}`).
`parse_query_result` handles the first two; `parse_range_result` handles the
third. Values are returned as strings by Prometheus's JSON API even though
they're numeric — always cast explicitly.
"""

from __future__ import annotations

from typing import Any

from app.domain.exceptions import InvalidPromQLError
from app.domain.metric import MetricSample, MetricSeries


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_promql(
    *,
    metric: str,
    job: str | None = None,
    tenant_id: str | None = None,
    query_text: str | None = None,
) -> str:
    """Build a PromQL instant-vector selector for the given metric + filters.

    `tenant_id` is a forward-compatible no-op today — no real metric carries
    a `tenant_id` label yet (see TODO.md Decision #3). The filter is built
    anyway so it starts working the moment that label is added upstream,
    without needing a second change here.
    """
    if not metric:
        raise InvalidPromQLError("metric name is required")

    matchers: list[str] = []
    if job:
        matchers.append(f'job="{_escape(job)}"')
    if tenant_id:
        matchers.append(f'tenant_id="{_escape(tenant_id)}"')
    if query_text:
        for pair in query_text.split(","):
            if "=" not in pair:
                raise InvalidPromQLError(f"Invalid q filter {pair!r}, expected key=value")
            key, value = pair.split("=", 1)
            key, value = key.strip(), value.strip()
            if not key:
                raise InvalidPromQLError(f"Invalid q filter {pair!r}, empty key")
            matchers.append(f'{key}="{_escape(value)}"')

    if not matchers:
        return metric
    return metric + "{" + ",".join(matchers) + "}"


def build_topk_promql(*, metric: str, n: int, job: str | None = None) -> str:
    if n <= 0:
        raise InvalidPromQLError("n must be a positive integer")
    selector = build_promql(metric=metric, job=job)
    return f"topk({n}, {selector})"


def parse_query_result(data: dict[str, Any]) -> list[MetricSample]:
    """Parse an instant-query (`vector` or `scalar`) response into `MetricSample`s."""
    result_data = data.get("data", {}) or {}
    result_type = result_data.get("resultType")
    result = result_data.get("result")

    if result_type == "scalar":
        if not isinstance(result, list) or len(result) != 2:
            return []
        ts, val = result
        return [MetricSample(metric_name="", labels={}, value=float(val), timestamp_s=float(ts))]

    if result_type == "vector":
        samples: list[MetricSample] = []
        for item in result or []:
            labels = dict(item.get("metric", {}))
            name = labels.pop("__name__", "")
            ts, val = item.get("value", [0, "0"])
            samples.append(
                MetricSample(
                    metric_name=name, labels=labels, value=float(val), timestamp_s=float(ts)
                )
            )
        return samples

    return []


def parse_range_result(data: dict[str, Any]) -> list[MetricSeries]:
    """Parse a range-query (`matrix`) response into `MetricSeries` objects."""
    result_data = data.get("data", {}) or {}
    result = result_data.get("result") or []
    series_list: list[MetricSeries] = []
    for item in result:
        labels = dict(item.get("metric", {}))
        name = labels.pop("__name__", "")
        values = [(float(ts), float(val)) for ts, val in item.get("values", [])]
        series_list.append(MetricSeries(metric_name=name, labels=labels, values=values))
    return series_list
