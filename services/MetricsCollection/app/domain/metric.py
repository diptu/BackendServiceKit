"""Internal representation of a metric sample/series, reshaped from Prometheus's
`/api/v1/query` and `/api/v1/query_range` responses.

Prometheus's HTTP API returns a different `data.resultType` depending on the
query shape: `vector` (one sample per series, from an instant query),
`matrix` (a list of samples per series, from a range query), or `scalar` (a
single unlabeled number). `app.repositories.metric_repository` normalizes all
three into these two dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricSample:
    """One instant value for one labeled series."""

    metric_name: str
    labels: dict[str, str]
    value: float
    timestamp_s: float


@dataclass(frozen=True)
class MetricSeries:
    """A labeled series with multiple (timestamp, value) points — a range-query result."""

    metric_name: str
    labels: dict[str, str]
    values: list[tuple[float, float]] = field(default_factory=list)
