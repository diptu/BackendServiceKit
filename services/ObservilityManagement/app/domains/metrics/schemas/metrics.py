"""Request/response schemas for the Metrics domain."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.core.schema_base import APIModel
from app.domains.metrics.repositories.metrics_repository import MetricSample


class MetricSampleResponse(APIModel):
    metric: dict[str, str] = Field(default_factory=dict)
    value: float
    timestamp: float

    @classmethod
    def from_domain(cls, sample: MetricSample) -> "MetricSampleResponse":
        return cls(metric=sample.metric, value=sample.value, timestamp=sample.timestamp)


class QueryResponse(APIModel):
    items: list[MetricSampleResponse]
    count: int


class SystemMetricsResponse(APIModel):
    data: dict[str, Any] = Field(default_factory=dict)


class PushRequest(APIModel):
    job: str
    metric_name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)


class PushResponse(APIModel):
    accepted: bool
