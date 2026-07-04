"""Investigation/correlation API — mounted at /api/v1/observability
(unchanged prefix, see TODO.md Decision #1)."""

from __future__ import annotations

import csv
import io
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.core.security import require_operator_scope
from app.domains.observability.dependencies import (
    get_anomaly_service,
    get_correlation_service,
    get_dashboard_service,
    get_incident_service,
    get_search_service,
    get_topology_service,
)
from app.domains.observability.schemas.observability import (
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
from app.domains.observability.services.anomaly_service import AnomalyService
from app.domains.observability.services.correlation_service import CorrelationService
from app.domains.observability.services.dashboard_service import DashboardService
from app.domains.observability.services.incident_service import IncidentService
from app.domains.observability.services.search_service import SearchService
from app.domains.observability.services.topology_service import TopologyService

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
    summary = await service.get_dashboard()
    return DashboardResponse.from_domain(summary)


@router.get("/search", response_model=SearchResponse)
async def search(
    service: SearchServiceDep,
    q: Annotated[str, Query()],
    minutes: Annotated[float, Query()] = 15.0,
    limit: Annotated[int, Query(le=200)] = 50,
) -> SearchResponse:
    results = await service.search(query=q, minutes=minutes, limit=limit)
    items = [SearchResultResponse.from_domain(r) for r in results]
    return SearchResponse(items=items, count=len(items))


@router.get("/incidents", response_model=IncidentsResponse)
async def get_incidents(service: IncidentServiceDep) -> IncidentsResponse:
    incidents = await service.list_incidents()
    items = [IncidentResponse.from_domain(i) for i in incidents]
    return IncidentsResponse(items=items, count=len(items))


@router.get("/dependencies", response_model=TopologyGraphResponse)
async def get_dependencies(
    service: TopologyServiceDep, minutes: Annotated[float, Query()] = 15.0
) -> TopologyGraphResponse:
    """Real observed service-call graph mined from trace data. Not the
    same as GET /api/v1/health/dependencies, which reports per-service
    dependency *health*, not call topology."""
    graph = await service.get_dependencies(minutes=minutes)
    return TopologyGraphResponse.from_domain(graph)


@router.get("/topology", response_model=TopologyGraphResponse)
async def get_topology(
    service: TopologyServiceDep, minutes: Annotated[float, Query()] = 15.0
) -> TopologyGraphResponse:
    graph = await service.get_topology(minutes=minutes)
    return TopologyGraphResponse.from_domain(graph)


@router.get("/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(service: AnomalyServiceDep) -> AnomaliesResponse:
    signals = await service.list_anomalies()
    items = [AnomalySignalResponse.from_domain(s) for s in signals]
    return AnomaliesResponse(items=items, count=len(items))


@router.get("/root-cause", response_model=EvidenceResponse)
async def get_root_cause(
    service: CorrelationServiceDep,
    alert_id: Annotated[str, Query(description="An Alerting alert fingerprint to investigate.")],
    minutes: Annotated[float, Query()] = 15.0,
) -> EvidenceResponse:
    evidence = await service.root_cause_for_alert(fingerprint=alert_id, minutes=minutes)
    items = [EvidenceItemResponse.from_domain(e) for e in evidence]
    return EvidenceResponse(items=items, count=len(items))


@router.get("/correlation", response_model=EvidenceResponse)
async def get_correlation(
    service: CorrelationServiceDep,
    target_service: Annotated[str, Query(alias="service")],
    minutes: Annotated[float, Query()] = 15.0,
) -> EvidenceResponse:
    evidence = await service.gather_evidence(service=target_service, minutes=minutes)
    items = [EvidenceItemResponse.from_domain(e) for e in evidence]
    return EvidenceResponse(items=items, count=len(items))


@router.get("/report", response_model=ReportResponse)
async def get_report(
    dashboard_service: DashboardServiceDep,
    incident_service: IncidentServiceDep,
    anomaly_service: AnomalyServiceDep,
) -> ReportResponse:
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
