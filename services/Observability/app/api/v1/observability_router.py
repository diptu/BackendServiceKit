"""Investigation/correlation API — see TODO.md Decisions #4-#10.

All paths are static/literal single segments under `/observability` — no
dynamic path segments, no literal-vs-dynamic ordering concern like
Alerting's/Monitoring's routers have.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import (
    get_anomaly_service,
    get_correlation_service,
    get_dashboard_service,
    get_incident_service,
    get_search_service,
    get_topology_service,
    require_operator_scope,
)
from app.core.config import settings
from app.schemas.observability import (
    AnomaliesResponse,
    AnomalySignalResponse,
    DashboardResponse,
    EvidenceItemResponse,
    EvidenceResponse,
    ExportRequest,
    ExportResponse,
    IncidentResponse,
    IncidentsResponse,
    ReportResponse,
    SearchResponse,
    SearchResultResponse,
    TopologyGraphResponse,
)
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.services.dashboard_service import DashboardService
from app.services.incident_service import IncidentService
from app.services.search_service import SearchService
from app.services.topology_service import TopologyService

router = APIRouter(
    prefix="/observability",
    tags=["Observability"],
    dependencies=[Depends(require_operator_scope)],
)

DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
TopologyServiceDep = Annotated[TopologyService, Depends(get_topology_service)]
IncidentServiceDep = Annotated[IncidentService, Depends(get_incident_service)]
AnomalyServiceDep = Annotated[AnomalyService, Depends(get_anomaly_service)]
CorrelationServiceDep = Annotated[CorrelationService, Depends(get_correlation_service)]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(service: DashboardServiceDep) -> DashboardResponse:
    """Five-way composition — TODO.md Decision #4."""
    summary = await service.get_dashboard()
    return DashboardResponse.from_domain(summary)


@router.get("/search", response_model=SearchResponse)
async def search(
    service: SearchServiceDep,
    q: Annotated[str, Query()],
    minutes: Annotated[float, Query()] = 15.0,
    limit: Annotated[int, Query(le=200)] = 50,
) -> SearchResponse:
    """Federated Logging + DistributedTracing search — TODO.md Decision #5."""
    results = await service.search(query=q, minutes=minutes, limit=limit)
    items = [SearchResultResponse.from_domain(r) for r in results]
    return SearchResponse(items=items, count=len(items))


@router.get("/incidents", response_model=IncidentsResponse)
async def get_incidents(service: IncidentServiceDep) -> IncidentsResponse:
    """Read-only reshaping of Alerting's active alerts — TODO.md Decision #6."""
    incidents = await service.list_incidents()
    items = [IncidentResponse.from_domain(i) for i in incidents]
    return IncidentsResponse(items=items, count=len(items))


@router.get("/dependencies", response_model=TopologyGraphResponse)
async def get_dependencies(
    service: TopologyServiceDep, minutes: Annotated[float, Query()] = 15.0
) -> TopologyGraphResponse:
    """Real observed service-call graph mined from trace data — TODO.md
    Decision #2. Not the same as HealthCheck's GET /health/dependencies,
    which reports per-service dependency *health*, not call topology."""
    graph = await service.get_dependencies(minutes=minutes)
    return TopologyGraphResponse.from_domain(graph)


@router.get("/topology", response_model=TopologyGraphResponse)
async def get_topology(
    service: TopologyServiceDep, minutes: Annotated[float, Query()] = 15.0
) -> TopologyGraphResponse:
    """Decision #2's graph with live health overlaid from HealthCheck —
    TODO.md Decision #3."""
    graph = await service.get_topology(minutes=minutes)
    return TopologyGraphResponse.from_domain(graph)


@router.get("/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(service: AnomalyServiceDep) -> AnomaliesResponse:
    """Simple, rule-based signals — TODO.md Decision #8. Not statistical/ML
    anomaly detection."""
    signals = await service.list_anomalies()
    items = [AnomalySignalResponse.from_domain(s) for s in signals]
    return AnomaliesResponse(items=items, count=len(items))


@router.get("/root-cause", response_model=EvidenceResponse)
async def get_root_cause(
    service: CorrelationServiceDep,
    alert_id: Annotated[str, Query(description="An Alerting alert fingerprint to investigate.")],
    minutes: Annotated[float, Query()] = 15.0,
) -> EvidenceResponse:
    """Correlated evidence for the service behind a specific alert —
    TODO.md Decision #7. An evidence panel, not an automated diagnosis."""
    evidence = await service.root_cause_for_alert(fingerprint=alert_id, minutes=minutes)
    items = [EvidenceItemResponse.from_domain(e) for e in evidence]
    return EvidenceResponse(items=items, count=len(items))


@router.get("/correlation", response_model=EvidenceResponse)
async def get_correlation(
    service: CorrelationServiceDep,
    target_service: Annotated[str, Query(alias="service")],
    minutes: Annotated[float, Query()] = 15.0,
) -> EvidenceResponse:
    """Correlated evidence for an explicit service+window — TODO.md
    Decision #7. Same engine as /root-cause, general-purpose entry point."""
    evidence = await service.gather_evidence(service=target_service, minutes=minutes)
    items = [EvidenceItemResponse.from_domain(e) for e in evidence]
    return EvidenceResponse(items=items, count=len(items))


@router.get("/report", response_model=ReportResponse)
async def get_report(
    dashboard_service: DashboardServiceDep,
    incident_service: IncidentServiceDep,
    anomaly_service: AnomalyServiceDep,
) -> ReportResponse:
    """Time-windowed rollup of /dashboard — TODO.md Decision #10. Computed
    on demand only, not a scheduled/emailed report."""
    summary = await dashboard_service.get_dashboard()
    incidents = await incident_service.list_incidents()
    anomalies = await anomaly_service.list_anomalies()
    return ReportResponse(
        window_minutes=settings.default_window_minutes,
        dashboard=DashboardResponse.from_domain(summary),
        incident_count=len(incidents),
        anomaly_count=len(anomalies),
    )


@router.post("/export", response_model=ExportResponse)
async def export(
    body: ExportRequest,
    dashboard_service: DashboardServiceDep,
    search_service: SearchServiceDep,
    correlation_service: CorrelationServiceDep,
) -> ExportResponse:
    """Serializes an already-computed result to JSON/CSV — TODO.md
    Decision #9. No new storage, no new computation."""
    data: Any
    if body.kind == "dashboard":
        summary = await dashboard_service.get_dashboard()
        data = DashboardResponse.from_domain(summary).model_dump()
    elif body.kind == "search":
        results = await search_service.search(query=body.query or "", minutes=body.minutes)
        data = [SearchResultResponse.from_domain(r).model_dump() for r in results]
    else:
        evidence = await correlation_service.gather_evidence(
            service=body.service or "", minutes=body.minutes
        )
        data = [EvidenceItemResponse.from_domain(e).model_dump() for e in evidence]

    content = _serialize(data, body.format)
    return ExportResponse(kind=body.kind, format=body.format, content=content)


def _serialize(data: Any, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(data, default=str)

    rows = data if isinstance(data, list) else [data]
    if not rows:
        return ""
    output = io.StringIO()
    fieldnames = sorted({k for row in rows for k in row})
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {k: (json.dumps(v) if isinstance(v, dict | list) else v) for k, v in row.items()}
        )
    return output.getvalue()
