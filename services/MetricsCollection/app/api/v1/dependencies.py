"""Operator-only access control + service wiring for the metrics API.

Same uniform single-tier model as DistributedTracing's `require_operator_scope`
— see TODO.md Decision #3 for why there is no tenant-self-service model here.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import Depends, Request

from app.core.config import settings
from app.domain.exceptions import NotAnOperatorError
from app.infrastructure.prometheus.prometheus_client import PrometheusClient
from app.infrastructure.pushgateway.pushgateway_client import PushgatewayClient
from app.middleware.auth import verify_token
from app.services.metric_ingest_service import MetricIngestService
from app.services.metric_query_service import MetricQueryService

PLATFORM_ADMIN_ROLE = "platform-admin"


async def require_operator_scope(
    claims: Annotated[dict[str, Any], Depends(verify_token)],
) -> None:
    """Gates every /metrics endpoint. No-op when jwt_auth_enabled=False."""
    if not settings.jwt_auth_enabled:
        return
    roles = claims.get("roles") or []
    if PLATFORM_ADMIN_ROLE not in roles:
        raise NotAnOperatorError()


def get_prometheus_client(request: Request) -> PrometheusClient:
    http_client: httpx.AsyncClient = request.app.state.http_client
    return PrometheusClient(http_client, settings.prometheus_base_url)


def get_pushgateway_client(request: Request) -> PushgatewayClient:
    http_client: httpx.AsyncClient = request.app.state.http_client
    return PushgatewayClient(http_client, settings.pushgateway_base_url)


def get_query_service(
    prometheus: Annotated[PrometheusClient, Depends(get_prometheus_client)],
) -> MetricQueryService:
    return MetricQueryService(prometheus)


def get_ingest_service(
    pushgateway: Annotated[PushgatewayClient, Depends(get_pushgateway_client)],
) -> MetricIngestService:
    return MetricIngestService(pushgateway, max_bulk_items=settings.metrics_bulk_max_items)
