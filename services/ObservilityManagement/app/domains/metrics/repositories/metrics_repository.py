"""Parses Prometheus's real instant/range query responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MetricSample:
    metric: dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    timestamp: float = 0.0


def parse_instant_query_response(raw: dict[str, Any]) -> list[MetricSample]:
    data = raw.get("data") or {}
    result = data.get("result")
    if not isinstance(result, list):
        return []

    samples: list[MetricSample] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        metric = item.get("metric") or {}
        value_pair = item.get("value")
        if not isinstance(value_pair, list) or len(value_pair) != 2:
            continue
        ts, val = value_pair
        try:
            samples.append(MetricSample(metric=dict(metric), value=float(val), timestamp=float(ts)))
        except (TypeError, ValueError):
            continue
    return samples
