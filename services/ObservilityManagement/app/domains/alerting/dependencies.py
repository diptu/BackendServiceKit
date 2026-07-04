"""Service wiring for the Alerting domain."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends

from app.core.config import settings
from app.core.dependencies import get_http_client
from app.domains.alerting.infrastructure.alertmanager_client import AlertmanagerClient
from app.domains.alerting.infrastructure.prometheus_rules_client import PrometheusRulesClient
from app.domains.alerting.infrastructure.rule_file_store import RuleFileStore
from app.domains.alerting.services.alert_service import AlertService
from app.domains.alerting.services.rule_service import RuleService

_rule_store = RuleFileStore(
    file_path=settings.managed_rules_file_path,
    group_name=settings.managed_rules_group_name,
)


def get_alertmanager_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> AlertmanagerClient:
    return AlertmanagerClient(http_client, settings.alertmanager_base_url)


def get_prometheus_rules_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> PrometheusRulesClient:
    return PrometheusRulesClient(http_client, settings.prometheus_base_url)


def get_alert_service(
    am_client: Annotated[AlertmanagerClient, Depends(get_alertmanager_client)],
) -> AlertService:
    return AlertService(am_client, default_ack_minutes=settings.default_acknowledge_minutes)


def get_rule_service(
    prom_client: Annotated[PrometheusRulesClient, Depends(get_prometheus_rules_client)],
) -> RuleService:
    return RuleService(
        _rule_store, prom_client, managed_group_name=settings.managed_rules_group_name
    )
