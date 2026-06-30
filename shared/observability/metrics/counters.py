"""Standard counter metric constructors."""

from __future__ import annotations

from opentelemetry.metrics import Counter, Meter


def make_request_counter(meter: Meter) -> Counter:
    return meter.create_counter(
        "http_requests_total",
        description="Total HTTP requests",
        unit="1",
    )


def make_error_counter(meter: Meter) -> Counter:
    return meter.create_counter(
        "http_errors_total",
        description="Total HTTP 5xx errors",
        unit="1",
    )


def make_cache_hit_counter(meter: Meter) -> Counter:
    return meter.create_counter(
        "cache_hits_total",
        description="Total cache hits",
        unit="1",
    )


def make_cache_miss_counter(meter: Meter) -> Counter:
    return meter.create_counter(
        "cache_misses_total",
        description="Total cache misses",
        unit="1",
    )
