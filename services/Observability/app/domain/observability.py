"""Domain model for the investigation/correlation API.

Every field being `None`/empty means "the source for this couldn't be
reached or had nothing to say," never "zero" — same convention every prior
aggregator in this series (Monitoring, HealthCheck) documents on its own
domain module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    """One piece of correlated evidence for root-cause/correlation views —
    TODO.md Decision #7. Not a verdict, just a time-aligned fact."""

    source: str  # "log" | "trace" | "metric" | "alert"
    timestamp: str
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    """One federated search hit — TODO.md Decision #5."""

    source: str  # "log" | "trace"
    timestamp: str
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TopologyEdge:
    """A real, observed service-to-service call, mined from trace data —
    TODO.md Decision #2. Never fabricated from static config."""

    caller: str
    callee: str
    call_count: int


@dataclass(frozen=True)
class TopologyNode:
    """One service in the topology graph, with live health overlaid from
    HealthCheck — TODO.md Decision #3."""

    name: str
    reachable: bool | None  # None = HealthCheck didn't have an opinion


@dataclass(frozen=True)
class TopologyGraph:
    nodes: list[TopologyNode] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)


@dataclass(frozen=True)
class Incident:
    """A read-only reshaping of Alerting's active alerts — TODO.md
    Decision #6. Not a second incident-tracking datastore."""

    alertname: str
    severity: str | None
    first_seen: str | None
    affected_services: list[str] = field(default_factory=list)
    fingerprints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnomalySignal:
    """A simple, rule-based signal — TODO.md Decision #8. Not a
    statistical/ML anomaly-detection result."""

    source: str  # "alert" | "metric"
    description: str
    severity: str


@dataclass(frozen=True)
class DashboardSummary:
    """The five-way composition from TODO.md Decision #4 — computes
    nothing itself, just gathers each sibling's own headline number."""

    error_log_count: int | None
    error_trace_count: int | None
    headline_metrics: dict[str, Any] = field(default_factory=dict)
    fleet_status: str | None = None
    active_alert_count: int | None = None
