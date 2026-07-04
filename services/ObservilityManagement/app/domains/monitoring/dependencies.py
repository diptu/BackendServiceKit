"""Service wiring for the Monitoring domain — pulls Alerting's AlertService
in-process (TODO.md Decision #4 applied within tier-3)."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends

from app.core.config import settings
from app.core.dependencies import get_http_client
from app.domains.alerting.dependencies import get_alert_service
from app.domains.alerting.services.alert_service import AlertService
from app.domains.monitoring.infrastructure.gateway_client import GatewayClient
from app.domains.monitoring.infrastructure.tenent_client import TenentClient
from app.domains.monitoring.services.monitoring_service import MonitoringService


def get_gateway_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> GatewayClient:
    return GatewayClient(http_client, settings.api_gateway_base_url)


def get_tenent_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> TenentClient:
    return TenentClient(http_client, settings.tenent_base_url)


def get_monitoring_service(
    gateway_client: Annotated[GatewayClient, Depends(get_gateway_client)],
    tenent_client: Annotated[TenentClient, Depends(get_tenent_client)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
) -> MonitoringService:
    return MonitoringService(gateway_client, tenent_client, alert_service)
