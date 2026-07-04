"""Domain model for the investigation/correlation API.

Every field being `None`/empty means "the source for this couldn't be
reached or had nothing to say," never "zero".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceItem:
    source: str  # "log" | "trace" | "metric" | "alert"
    timestamp: str
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    source: str  # "log" | "trace"
    timestamp: str
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TopologyEdge:
    caller: str
    callee: str
    call_count: int


@dataclass(frozen=True)
class TopologyNode:
    name: str
    reachable: bool | None  # None = Health domain didn't have an opinion


@dataclass(frozen=True)
class TopologyGraph:
    nodes: list[TopologyNode] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)


@dataclass(frozen=True)
class Incident:
    alertname: str
    severity: str | None
    first_seen: str | None
    affected_services: list[str] = field(default_factory=list)
    fingerprints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnomalySignal:
    source: str  # "alert" | "metric"
    description: str
    severity: str


@dataclass(frozen=True)
class DashboardSummary:
    error_log_count: int | None
    error_trace_count: int | None
    headline_metrics: dict[str, Any] = field(default_factory=dict)
    fleet_status: str | None = None
    active_alert_count: int | None = None
