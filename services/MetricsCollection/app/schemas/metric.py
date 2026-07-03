"""Request/response schemas for the metrics API."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.metric import MetricSample, MetricSeries
from app.schemas.base import APIModel


class MetricSampleResponse(APIModel):
    metric_name: str
    labels: dict[str, str] = Field(default_factory=dict)
    value: float
    timestamp_s: float

    @classmethod
    def from_sample(cls, sample: MetricSample) -> "MetricSampleResponse":
        return cls(
            metric_name=sample.metric_name,
            labels=sample.labels,
            value=sample.value,
            timestamp_s=sample.timestamp_s,
        )


class MetricSeriesResponse(APIModel):
    metric_name: str
    labels: dict[str, str] = Field(default_factory=dict)
    values: list[tuple[float, float]] = Field(default_factory=list)

    @classmethod
    def from_series(cls, series: MetricSeries) -> "MetricSeriesResponse":
        return cls(metric_name=series.metric_name, labels=series.labels, values=series.values)


class MetricQueryResponse(APIModel):
    items: list[MetricSampleResponse]
    count: int


class MetricHistoryResponse(APIModel):
    items: list[MetricSeriesResponse]
    count: int


class MetricListResponse(APIModel):
    names: list[str]
    count: int


class MetricPushCreate(APIModel):
    """A single metric point submitted via the Pushgateway escape hatch.

    `timestamp` is accepted for compatibility with the README's example
    shape but is not forwarded to Pushgateway — Pushgateway does not support
    custom sample timestamps; every pushed value is reported as "now" at the
    moment Prometheus next scrapes it (see TODO.md Decision #4).
    """

    metric: str
    value: float
    job: str = "external"
    labels: dict[str, str] = Field(default_factory=dict)
    metric_type: Literal["gauge", "counter"] = "gauge"
    timestamp: str | None = None


class MetricsBulkPush(APIModel):
    items: list[MetricPushCreate]


class PushAcceptedResponse(APIModel):
    accepted: int


class DeleteAcceptedResponse(APIModel):
    job: str
    labels: dict[str, str] = Field(default_factory=dict)
