"""Prometheus metrics for the Tenent service."""

from __future__ import annotations

from prometheus_client import (  # type: ignore[import-untyped]
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)

REGISTRY = CollectorRegistry(auto_describe=True)

isolation_decisions_total = Counter(
    "isolation_decisions_total",
    "Total isolation access decisions",
    ["decision"],
    registry=REGISTRY,
)

isolation_violations_total = Counter(
    "isolation_violations_total",
    "Total cross-tenant isolation violations detected",
    registry=REGISTRY,
)

isolation_resource_claims_total = Counter(
    "isolation_resource_claims_total",
    "Total resource claims registered",
    registry=REGISTRY,
)

isolation_active_policies = Gauge(
    "isolation_active_policies",
    "Current number of active isolation policies",
    registry=REGISTRY,
)

isolation_check_duration = Histogram(
    "isolation_check_duration_seconds",
    "Duration of isolation access checks",
    ["endpoint"],
    registry=REGISTRY,
)
