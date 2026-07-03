"""Operator-only access control + service wiring.

Same uniform single-tier `require_operator_scope` model as every tier-3
service in this series — see TODO.md Decision #13.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import Depends, Request

from app.core.config import settings
from app.domain.exceptions import NotAnOperatorError
from app.infrastructure.siblings.alerting_client import AlertingClient
from app.infrastructure.siblings.health_client import HealthClient
from app.infrastructure.siblings.logging_client import LoggingClient
from app.infrastructure.siblings.metrics_client import MetricsClient
from app.infrastructure.siblings.monitoring_client import MonitoringClient
from app.infrastructure.siblings.tracing_client import TracingClient
from app.middleware.auth import verify_token
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.services.dashboard_service import DashboardService
from app.services.incident_service import IncidentService
from app.services.search_service import SearchService
from app.services.topology_service import TopologyService

PLATFORM_ADMIN_ROLE = "platform-admin"


async def require_operator_scope(
    claims: Annotated[dict[str, Any], Depends(verify_token)],
) -> None:
    """Gates every /observability endpoint. No-op when jwt_auth_enabled=False."""
    if not settings.jwt_auth_enabled:
        return
    roles = claims.get("roles") or []
    if PLATFORM_ADMIN_ROLE not in roles:
        raise NotAnOperatorError()


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient = request.app.state.http_client
    return client


def get_logging_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> LoggingClient:
    return LoggingClient(http_client, settings.logging_base_url)


def get_tracing_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> TracingClient:
    return TracingClient(http_client, settings.distributed_tracing_base_url)


def get_metrics_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> MetricsClient:
    return MetricsClient(http_client, settings.metrics_collection_base_url)


def get_monitoring_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> MonitoringClient:
    return MonitoringClient(http_client, settings.monitoring_base_url)


def get_alerting_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> AlertingClient:
    return AlertingClient(http_client, settings.alerting_base_url)


def get_health_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> HealthClient:
    return HealthClient(http_client, settings.health_check_base_url)


def get_dashboard_service(
    logging_client: Annotated[LoggingClient, Depends(get_logging_client)],
    tracing_client: Annotated[TracingClient, Depends(get_tracing_client)],
    metrics_client: Annotated[MetricsClient, Depends(get_metrics_client)],
    health_client: Annotated[HealthClient, Depends(get_health_client)],
    alerting_client: Annotated[AlertingClient, Depends(get_alerting_client)],
) -> DashboardService:
    return DashboardService(
        logging_client,
        tracing_client,
        metrics_client,
        health_client,
        alerting_client,
        window_minutes=settings.default_window_minutes,
    )


def get_search_service(
    logging_client: Annotated[LoggingClient, Depends(get_logging_client)],
    tracing_client: Annotated[TracingClient, Depends(get_tracing_client)],
) -> SearchService:
    return SearchService(logging_client, tracing_client)


def get_topology_service(
    tracing_client: Annotated[TracingClient, Depends(get_tracing_client)],
    health_client: Annotated[HealthClient, Depends(get_health_client)],
) -> TopologyService:
    return TopologyService(tracing_client, health_client)


def get_incident_service(
    alerting_client: Annotated[AlertingClient, Depends(get_alerting_client)],
) -> IncidentService:
    return IncidentService(alerting_client)


def get_anomaly_service(
    alerting_client: Annotated[AlertingClient, Depends(get_alerting_client)],
) -> AnomalyService:
    return AnomalyService(alerting_client)


def get_correlation_service(
    logging_client: Annotated[LoggingClient, Depends(get_logging_client)],
    tracing_client: Annotated[TracingClient, Depends(get_tracing_client)],
    metrics_client: Annotated[MetricsClient, Depends(get_metrics_client)],
    alerting_client: Annotated[AlertingClient, Depends(get_alerting_client)],
) -> CorrelationService:
    return CorrelationService(logging_client, tracing_client, metrics_client, alerting_client)
