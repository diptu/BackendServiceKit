"""Prometheus metrics for provisioning jobs."""
from __future__ import annotations

from prometheus_client import (  # type: ignore[import-untyped]
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)

REGISTRY = CollectorRegistry(auto_describe=True)

provisioning_jobs_started = Counter(
    "provisioning_jobs_started_total",
    "Total provisioning jobs started",
    registry=REGISTRY,
)

provisioning_jobs_completed = Counter(
    "provisioning_jobs_completed_total",
    "Total provisioning jobs completed",
    registry=REGISTRY,
)

provisioning_jobs_failed = Counter(
    "provisioning_jobs_failed_total",
    "Total provisioning jobs failed",
    registry=REGISTRY,
)

provisioning_step_duration = Histogram(
    "provisioning_step_duration_seconds",
    "Duration of individual provisioning steps",
    ["step"],
    registry=REGISTRY,
)

provisioning_queue_depth = Gauge(
    "provisioning_queue_depth",
    "Current number of pending or running jobs",
    registry=REGISTRY,
)
