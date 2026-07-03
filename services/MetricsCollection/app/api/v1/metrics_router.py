"""The metrics API — list, query, history, derived views, push, delete.

Every route on this router is gated by `require_operator_scope` (applied
once at router level below — see TODO.md Decision #3). Route registration
order doesn't actually matter here (unlike Logging's `/{id}` or
DistributedTracing's `/{trace_id}` catch-alls): the only dynamic single-segment
path is `DELETE /{job}`, and no other route under `/metrics` collides with it
on method + path shape.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_ingest_service, get_query_service, require_operator_scope
from app.domain.exceptions import ScrapedMetricDeleteNotSupportedError
from app.schemas.metric import (
    DeleteAcceptedResponse,
    MetricHistoryResponse,
    MetricListResponse,
    MetricPushCreate,
    MetricQueryResponse,
    MetricSampleResponse,
    MetricSeriesResponse,
    MetricsBulkPush,
    PushAcceptedResponse,
)
from app.services.metric_ingest_service import MetricIngestService
from app.services.metric_query_service import MetricQueryService

router = APIRouter(prefix="/metrics", dependencies=[Depends(require_operator_scope)])

_ONE_HOUR_S = 3_600

# Self-scrape jobs whose default prometheus_client registry includes
# ProcessCollector/PlatformCollector (see TODO.md Phase 5/Decision #6) —
# Tenent's own local CollectorRegistry does NOT, since it's a bare instance,
# not the module-default one those collectors auto-register onto.
_SYSTEM_METRIC_NAMES = ("process_resident_memory_bytes", "process_cpu_seconds_total")


def _default_window() -> tuple[int, int]:
    end_s = int(time.time())
    return end_s - _ONE_HOUR_S, end_s


def _to_s(dt: datetime | None) -> int | None:
    return int(dt.timestamp()) if dt is not None else None


@router.get(
    "",
    tags=["Metrics — Query"],
    summary="List known metric names",
    response_model=MetricListResponse,
)
async def list_metrics(
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
    prefix: str | None = Query(default=None, description="Only names starting with this prefix"),
    contains: str | None = Query(default=None, description="Only names containing this substring"),
) -> MetricListResponse:
    names = await query_service.list_metric_names()
    if prefix:
        names = [n for n in names if n.startswith(prefix)]
    if contains:
        names = [n for n in names if contains in n]
    return MetricListResponse(names=sorted(names), count=len(names))


@router.get(
    "/query",
    tags=["Metrics — Query"],
    summary="Instant query for a metric",
    response_model=MetricQueryResponse,
)
async def query_metric(
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
    metric: str = Query(..., description="Metric name, e.g. isolation_decisions_total"),
    job: str | None = Query(default=None, description="Filter by the Prometheus job label"),
    tenant_id: str | None = Query(
        default=None, description="Currently a no-op — see TODO.md Decision #3"
    ),
    q: str | None = Query(
        default=None, description="Additional label filter: key=value[,key2=value2]"
    ),
) -> MetricQueryResponse:
    samples = await query_service.query(metric=metric, job=job, tenant_id=tenant_id, query_text=q)
    items = [MetricSampleResponse.from_sample(s) for s in samples]
    return MetricQueryResponse(items=items, count=len(items))


@router.get(
    "/history",
    tags=["Metrics — Query"],
    summary="Range query (time series history) for a metric",
    response_model=MetricHistoryResponse,
)
async def metric_history(
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
    metric: str = Query(...),
    job: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    step: str = Query(default="60s"),
) -> MetricHistoryResponse:
    default_start, default_end = _default_window()
    series = await query_service.history(
        metric=metric,
        job=job,
        tenant_id=tenant_id,
        query_text=q,
        start_s=_to_s(start) or default_start,
        end_s=_to_s(end) or default_end,
        step=step,
    )
    items = [MetricSeriesResponse.from_series(s) for s in series]
    return MetricHistoryResponse(items=items, count=len(items))


@router.get(
    "/service/{service}",
    tags=["Metrics — Query"],
    summary="Query a metric scoped to one service",
    response_model=MetricQueryResponse,
)
async def metric_by_service(
    service: str,
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
    metric: str = Query(...),
) -> MetricQueryResponse:
    # `job` is the real, always-present Prometheus label (from scrape_configs'
    # job_name) — not `service.name`, which only exists on the dead OTel
    # metrics pipeline (see TODO.md Decision #1).
    samples = await query_service.query(metric=metric, job=service)
    items = [MetricSampleResponse.from_sample(s) for s in samples]
    return MetricQueryResponse(items=items, count=len(items))


@router.get(
    "/tenant/{tenant}",
    tags=["Metrics — Query"],
    summary="Query a metric scoped to one tenant — currently a no-op (see TODO.md Decision #3)",
    response_model=MetricQueryResponse,
)
async def metric_by_tenant(
    tenant: str,
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
    metric: str = Query(...),
) -> MetricQueryResponse:
    samples = await query_service.query(metric=metric, tenant_id=tenant)
    items = [MetricSampleResponse.from_sample(s) for s in samples]
    return MetricQueryResponse(items=items, count=len(items))


@router.get(
    "/top",
    tags=["Metrics — Query"],
    summary="Top-N series for a metric",
    response_model=MetricQueryResponse,
)
async def top_metrics(
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
    metric: str = Query(...),
    n: int = Query(default=5, ge=1, le=100),
    job: str | None = Query(default=None),
) -> MetricQueryResponse:
    samples = await query_service.top(metric=metric, n=n, job=job)
    items = [MetricSampleResponse.from_sample(s) for s in samples]
    return MetricQueryResponse(items=items, count=len(items))


@router.get(
    "/system",
    tags=["Metrics — Query"],
    summary="Process-level system metrics (CPU, memory) for every scraped job that exposes them",
    response_model=MetricQueryResponse,
    description=(
        "Scoped to whatever `prometheus_client`'s default ProcessCollector "
        "already exposes for services using the default registry "
        "(api-gateway, logging, distributed-tracing, metrics-collection). "
        "Tenent built its own bare CollectorRegistry, which does not "
        "auto-register ProcessCollector, so it won't appear here. No "
        "node-exporter/cAdvisor is deployed for real host-level metrics — "
        "see TODO.md Decision #6."
    ),
)
async def system_metrics(
    query_service: Annotated[MetricQueryService, Depends(get_query_service)],
) -> MetricQueryResponse:
    all_samples = []
    for name in _SYSTEM_METRIC_NAMES:
        all_samples.extend(await query_service.query(metric=name))
    items = [MetricSampleResponse.from_sample(s) for s in all_samples]
    return MetricQueryResponse(items=items, count=len(items))


@router.post(
    "",
    tags=["Metrics — Push"],
    summary="Push a single metric point (escape hatch — see tag description)",
    response_model=PushAcceptedResponse,
    status_code=202,
)
async def push_metric(
    body: MetricPushCreate,
    ingest_service: Annotated[MetricIngestService, Depends(get_ingest_service)],
) -> PushAcceptedResponse:
    accepted = await ingest_service.push_one(body)
    return PushAcceptedResponse(accepted=accepted)


@router.post(
    "/bulk",
    tags=["Metrics — Push"],
    summary="Push a batch of metric points (escape hatch — see tag description)",
    response_model=PushAcceptedResponse,
    status_code=202,
)
async def push_metrics_bulk(
    body: MetricsBulkPush,
    ingest_service: Annotated[MetricIngestService, Depends(get_ingest_service)],
) -> PushAcceptedResponse:
    accepted = await ingest_service.push_bulk(body.items)
    return PushAcceptedResponse(accepted=accepted)


@router.delete(
    "/{job}",
    tags=["Metrics — Push"],
    summary="Delete previously-pushed metrics for a job (real — see TODO.md Decision #5)",
    response_model=DeleteAcceptedResponse,
)
async def delete_metrics_for_job(
    job: str,
    ingest_service: Annotated[MetricIngestService, Depends(get_ingest_service)],
) -> DeleteAcceptedResponse:
    await ingest_service.delete(job=job)
    return DeleteAcceptedResponse(job=job, labels={})


@router.delete(
    "",
    tags=["Metrics — Push"],
    summary="Not supported without a job — see TODO.md Decision #5",
)
async def delete_metrics_no_job() -> None:
    raise ScrapedMetricDeleteNotSupportedError()
