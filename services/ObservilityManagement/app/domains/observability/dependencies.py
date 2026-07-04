"""Service wiring for the Observability domain — pulls every other
domain's service class in-process (TODO.md Decision #4)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.domains.alerting.dependencies import get_alert_service
from app.domains.alerting.services.alert_service import AlertService
from app.domains.health.dependencies import get_health_service
from app.domains.health.services.health_service import HealthService
from app.domains.logging.dependencies import get_log_query_service
from app.domains.logging.services.log_query_service import LogQueryService
from app.domains.metrics.dependencies import get_metrics_query_service
from app.domains.metrics.services.metrics_query_service import MetricsQueryService
from app.domains.observability.services.anomaly_service import AnomalyService
from app.domains.observability.services.correlation_service import CorrelationService
from app.domains.observability.services.dashboard_service import DashboardService
from app.domains.observability.services.incident_service import IncidentService
from app.domains.observability.services.search_service import SearchService
from app.domains.observability.services.topology_service import TopologyService
from app.domains.tracing.dependencies import get_trace_query_service
from app.domains.tracing.services.trace_query_service import TraceQueryService


def get_dashboard_service(
    log_service: Annotated[LogQueryService, Depends(get_log_query_service)],
    trace_service: Annotated[TraceQueryService, Depends(get_trace_query_service)],
    metrics_service: Annotated[MetricsQueryService, Depends(get_metrics_query_service)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> DashboardService:
    return DashboardService(
        log_service,
        trace_service,
        metrics_service,
        health_service,
        alert_service,
        window_minutes=settings.default_window_minutes,
    )


def get_search_service(
    log_service: Annotated[LogQueryService, Depends(get_log_query_service)],
    trace_service: Annotated[TraceQueryService, Depends(get_trace_query_service)],
) -> SearchService:
    return SearchService(log_service, trace_service)


def get_topology_service(
    trace_service: Annotated[TraceQueryService, Depends(get_trace_query_service)],
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> TopologyService:
    return TopologyService(trace_service, health_service)


def get_incident_service(
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> IncidentService:
    return IncidentService(alert_service)


def get_anomaly_service(
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> AnomalyService:
    return AnomalyService(alert_service)


def get_correlation_service(
    log_service: Annotated[LogQueryService, Depends(get_log_query_service)],
    trace_service: Annotated[TraceQueryService, Depends(get_trace_query_service)],
    metrics_service: Annotated[MetricsQueryService, Depends(get_metrics_query_service)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> CorrelationService:
    return CorrelationService(log_service, trace_service, metrics_service, alert_service)
