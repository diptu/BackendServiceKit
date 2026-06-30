"""Standard histogram metric constructors."""

from __future__ import annotations

from opentelemetry.metrics import Histogram, Meter


def make_request_duration_histogram(meter: Meter) -> Histogram:
    return meter.create_histogram(
        "http_request_duration_seconds",
        description="HTTP request duration",
        unit="s",
    )


def make_db_query_duration_histogram(meter: Meter) -> Histogram:
    return meter.create_histogram(
        "db_query_duration_seconds",
        description="Database query duration",
        unit="s",
    )


def make_cache_operation_duration_histogram(meter: Meter) -> Histogram:
    return meter.create_histogram(
        "cache_operation_duration_seconds",
        description="Cache operation duration",
        unit="s",
    )
