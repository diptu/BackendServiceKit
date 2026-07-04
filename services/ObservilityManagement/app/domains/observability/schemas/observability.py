"""Request/response schemas for the investigation/correlation API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.core.schema_base import APIModel
from app.domains.observability.models import (
    AnomalySignal,
    DashboardSummary,
    EvidenceItem,
    Incident,
    SearchResult,
    TopologyEdge,
    TopologyGraph,
    TopologyNode,
)


class DashboardResponse(APIModel):
    error_log_count: int | None
    error_trace_count: int | None
    headline_metrics: dict[str, Any] = Field(default_factory=dict)
    fleet_status: str | None = None
    active_alert_count: int | None = None

    @classmethod
    def from_domain(cls, summary: DashboardSummary) -> "DashboardResponse":
        return cls(
            error_log_count=summary.error_log_count,
            error_trace_count=summary.error_trace_count,
            headline_metrics=summary.headline_metrics,
            fleet_status=summary.fleet_status,
            active_alert_count=summary.active_alert_count,
        )


class SearchResultResponse(APIModel):
    source: str
    timestamp: str
    summary: str
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, result: SearchResult) -> "SearchResultResponse":
        return cls(
            source=result.source, timestamp=result.timestamp, summary=result.summary, raw=result.raw
        )


class SearchResponse(APIModel):
    items: list[SearchResultResponse]
    count: int


class TopologyNodeResponse(APIModel):
    name: str
    reachable: bool | None

    @classmethod
    def from_domain(cls, node: TopologyNode) -> "TopologyNodeResponse":
        return cls(name=node.name, reachable=node.reachable)


class TopologyEdgeResponse(APIModel):
    caller: str
    callee: str
    call_count: int

    @classmethod
    def from_domain(cls, edge: TopologyEdge) -> "TopologyEdgeResponse":
        return cls(caller=edge.caller, callee=edge.callee, call_count=edge.call_count)


class TopologyGraphResponse(APIModel):
    nodes: list[TopologyNodeResponse]
    edges: list[TopologyEdgeResponse]

    @classmethod
    def from_domain(cls, graph: TopologyGraph) -> "TopologyGraphResponse":
        return cls(
            nodes=[TopologyNodeResponse.from_domain(n) for n in graph.nodes],
            edges=[TopologyEdgeResponse.from_domain(e) for e in graph.edges],
        )


class IncidentResponse(APIModel):
    alertname: str
    severity: str | None
    first_seen: str | None
    affected_services: list[str] = Field(default_factory=list)
    fingerprints: list[str] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, incident: Incident) -> "IncidentResponse":
        return cls(
            alertname=incident.alertname,
            severity=incident.severity,
            first_seen=incident.first_seen,
            affected_services=incident.affected_services,
            fingerprints=incident.fingerprints,
        )


class IncidentsResponse(APIModel):
    items: list[IncidentResponse]
    count: int


class AnomalySignalResponse(APIModel):
    source: str
    description: str
    severity: str

    @classmethod
    def from_domain(cls, signal: AnomalySignal) -> "AnomalySignalResponse":
        return cls(source=signal.source, description=signal.description, severity=signal.severity)


class AnomaliesResponse(APIModel):
    items: list[AnomalySignalResponse]
    count: int


class EvidenceItemResponse(APIModel):
    source: str
    timestamp: str
    summary: str
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, item: EvidenceItem) -> "EvidenceItemResponse":
        return cls(source=item.source, timestamp=item.timestamp, summary=item.summary, raw=item.raw)


class EvidenceResponse(APIModel):
    items: list[EvidenceItemResponse]
    count: int


class ExportRequest(APIModel):
    kind: Literal["dashboard", "search", "correlation"]
    format: Literal["json", "csv"] = "json"
    query: str | None = None
    service: str | None = None
    minutes: float = 15.0


class ExportResponse(APIModel):
    kind: str
    format: str
    content: str


class ReportResponse(APIModel):
    window_minutes: float
    dashboard: DashboardResponse
    incident_count: int
    anomaly_count: int
