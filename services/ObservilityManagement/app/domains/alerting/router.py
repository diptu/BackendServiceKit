"""Alerting domain router — mounted at /api/v1/alerts (unchanged prefix,
see TODO.md Decision #1).

Route order matters: `/rules` and `/test` are literal one-segment paths
and must be registered *before* `/{fingerprint}` (a dynamic one-segment
path) — otherwise FastAPI would match `GET /alerts/rules` as
`GET /alerts/{fingerprint}` with fingerprint="rules".
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import require_operator_scope
from app.domains.alerting.dependencies import get_alert_service, get_rule_service
from app.domains.alerting.schemas.alert import (
    AcknowledgeRequest,
    AcknowledgeResponse,
    AlertListResponse,
    AlertPushCreate,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleStatusListResponse,
    AlertRuleStatusResponse,
    PushAcceptedResponse,
    ResolveResponse,
    RuleMutationResponse,
    TestAlertResponse,
)
from app.domains.alerting.services.alert_service import AlertService
from app.domains.alerting.services.rule_service import RuleService

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"],
    dependencies=[Depends(require_operator_scope)],
)

AlertServiceDep = Annotated[AlertService, Depends(get_alert_service)]
RuleServiceDep = Annotated[RuleService, Depends(get_rule_service)]


@router.post("", response_model=PushAcceptedResponse, status_code=202)
async def push_alert(body: AlertPushCreate, service: AlertServiceDep) -> PushAcceptedResponse:
    await service.push_alert(
        labels=body.labels,
        annotations=body.annotations,
        generator_url=body.generator_url,
        ends_in_minutes=body.ends_in_minutes,
    )
    return PushAcceptedResponse(accepted=True)


@router.get("", response_model=AlertListResponse)
async def list_alerts(service: AlertServiceDep) -> AlertListResponse:
    alerts = await service.list_alerts()
    items = [AlertResponse.from_domain(a) for a in alerts]
    return AlertListResponse(items=items, count=len(items))


@router.post("/test", response_model=TestAlertResponse)
async def send_test_alert(service: AlertServiceDep) -> TestAlertResponse:
    result = await service.send_test_alert()
    return TestAlertResponse(labels=result["labels"], annotations=result["annotations"])


@router.get("/rules", response_model=AlertRuleStatusListResponse)
async def list_rules(
    rule_service: RuleServiceDep,
    managed_only: Annotated[bool, Query()] = False,
) -> AlertRuleStatusListResponse:
    statuses = await rule_service.list_rule_statuses()
    items = [
        AlertRuleStatusResponse.from_domain(s, managed=rule_service.is_managed(s))
        for s in statuses
        if not managed_only or rule_service.is_managed(s)
    ]
    return AlertRuleStatusListResponse(items=items, count=len(items))


@router.post("/rules", response_model=RuleMutationResponse, status_code=201)
async def create_rule(body: AlertRuleCreate, rule_service: RuleServiceDep) -> RuleMutationResponse:
    await rule_service.create_rule(body.to_domain())
    return RuleMutationResponse(name=body.name, reloaded=True)


@router.put("/rules/{name}", response_model=RuleMutationResponse)
async def update_rule(
    name: str, body: AlertRuleCreate, rule_service: RuleServiceDep
) -> RuleMutationResponse:
    await rule_service.update_rule(name, body.to_domain())
    return RuleMutationResponse(name=name, reloaded=True)


@router.delete("/rules/{name}", response_model=RuleMutationResponse)
async def delete_rule(name: str, rule_service: RuleServiceDep) -> RuleMutationResponse:
    await rule_service.delete_rule(name)
    return RuleMutationResponse(name=name, reloaded=True)


@router.get("/{fingerprint}", response_model=AlertResponse)
async def get_alert(fingerprint: str, service: AlertServiceDep) -> AlertResponse:
    alert = await service.get_alert(fingerprint)
    return AlertResponse.from_domain(alert)


@router.patch("/{fingerprint}/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_alert(
    fingerprint: str, body: AcknowledgeRequest, service: AlertServiceDep
) -> AcknowledgeResponse:
    silence_id = await service.acknowledge(
        fingerprint,
        duration_minutes=body.duration_minutes,
        comment=body.comment,
        created_by=body.created_by,
    )
    return AcknowledgeResponse(silence_id=silence_id)


@router.patch("/{fingerprint}/resolve", response_model=ResolveResponse)
async def resolve_alert(fingerprint: str, service: AlertServiceDep) -> ResolveResponse:
    await service.resolve(fingerprint)
    return ResolveResponse(resolved=True)
