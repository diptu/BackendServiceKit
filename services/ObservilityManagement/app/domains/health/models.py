"""Domain model for normalized fleet health.

A `status` of "unknown" means "this target's `/ready` didn't mention this
dependency in a shape we recognize," never conflated with "down".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    status: str  # "up" | "down" | "unknown"
    latency_ms: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class ServiceHealth:
    name: str
    base_url: str
    reachable: bool
    version: str | None = None
    observed_uptime_seconds: float | None = None
    dependencies: list[DependencyStatus] = field(default_factory=list)
    raw_health: dict[str, Any] | None = None
    raw_ready: dict[str, Any] | None = None


@dataclass(frozen=True)
class FleetHealth:
    overall_status: str
    services: list[ServiceHealth] = field(default_factory=list)
