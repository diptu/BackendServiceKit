"""Traces domain router — mounted at /api/v1/traces (unchanged prefix,
see TODO.md Decision #1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import require_operator_scope
from app.domains.tracing.dependencies import get_trace_query_service
from app.domains.tracing.schemas.trace import TraceSearchResponse, TraceSummaryResponse
from app.domains.tracing.services.trace_query_service import TraceQueryService

router = APIRouter(
    prefix="/traces",
    tags=["Traces"],
    dependencies=[Depends(require_operator_scope)],
)

TraceQueryServiceDep = Annotated[TraceQueryService, Depends(get_trace_query_service)]


@router.get("/search", response_model=TraceSearchResponse)
async def search(
    service: TraceQueryServiceDep,
    query: Annotated[str, Query()] = "",
    minutes: Annotated[float, Query()] = 15.0,
    limit: Annotated[int, Query(le=200)] = 20,
) -> TraceSearchResponse:
    summaries = await service.search(query=query, minutes=minutes, limit=limit)
    items = [TraceSummaryResponse.from_domain(s) for s in summaries]
    return TraceSearchResponse(items=items, count=len(items))
