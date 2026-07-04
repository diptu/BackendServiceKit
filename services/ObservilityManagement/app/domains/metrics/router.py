"""Metrics domain router — mounted at /api/v1/metrics (unchanged prefix,
see TODO.md Decision #1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import require_operator_scope
from app.domains.metrics.dependencies import get_metrics_query_service
from app.domains.metrics.schemas.metrics import (
    MetricSampleResponse,
    PushRequest,
    PushResponse,
    QueryResponse,
    SystemMetricsResponse,
)
from app.domains.metrics.services.metrics_query_service import MetricsQueryService

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
    dependencies=[Depends(require_operator_scope)],
)

MetricsQueryServiceDep = Annotated[MetricsQueryService, Depends(get_metrics_query_service)]


@router.get("/query", response_model=QueryResponse)
async def query(service: MetricsQueryServiceDep, promql: Annotated[str, Query()]) -> QueryResponse:
    samples = await service.query(promql=promql)
    items = [MetricSampleResponse.from_domain(s) for s in samples]
    return QueryResponse(items=items, count=len(items))


@router.get("/system", response_model=SystemMetricsResponse)
async def system_metrics(service: MetricsQueryServiceDep) -> SystemMetricsResponse:
    data = await service.system_metrics()
    return SystemMetricsResponse(data=data or {})


@router.post("/push", response_model=PushResponse, status_code=202)
async def push(service: MetricsQueryServiceDep, body: PushRequest) -> PushResponse:
    accepted = await service.push(
        job=body.job, metric_name=body.metric_name, value=body.value, labels=body.labels
    )
    return PushResponse(accepted=accepted)
