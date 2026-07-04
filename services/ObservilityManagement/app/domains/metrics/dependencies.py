"""Service wiring for the Metrics domain."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends

from app.core.config import settings
from app.core.dependencies import get_http_client
from app.domains.metrics.infrastructure.prometheus_client import PrometheusClient
from app.domains.metrics.infrastructure.pushgateway_client import PushgatewayClient
from app.domains.metrics.services.metrics_query_service import MetricsQueryService


def get_prometheus_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> PrometheusClient:
    return PrometheusClient(http_client, settings.prometheus_base_url)


def get_pushgateway_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> PushgatewayClient:
    return PushgatewayClient(http_client, settings.pushgateway_base_url)


def get_metrics_query_service(
    prometheus_client: Annotated[PrometheusClient, Depends(get_prometheus_client)],
    pushgateway_client: Annotated[PushgatewayClient, Depends(get_pushgateway_client)],
) -> MetricsQueryService:
    return MetricsQueryService(prometheus_client, pushgateway_client)
