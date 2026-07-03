"""The traces API — search, fetch by id, derived views, export.

Every route on this router is gated by `require_operator_scope` (applied
once at router level below — see TODO.md Decision #3 for why this service
has one uniform access tier instead of Logging's tenant/platform-admin split).

Route registration order matters for the single-segment paths: `/search`,
`/service/{service}`, `/errors`, `/slow`, and `/export` MUST be declared
before the dynamic `/{trace_id}` route below them, or FastAPI would match
e.g. `/traces/search` as `/traces/{trace_id}` with `trace_id="search"`.
`/{trace_id}/timeline` and `/{trace_id}/spans` don't have this problem —
they have an extra path segment, so they never collide with the one-segment
routes regardless of registration order.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.v1.dependencies import get_export_service, get_query_service, require_operator_scope
from app.schemas.trace import (
    SpansResponse,
    TimelineResponse,
    TraceResponse,
    TraceSearchResponse,
    TraceSummaryResponse,
)
from app.services.trace_export_service import TraceExportService
from app.services.trace_query_service import TraceQueryService

router = APIRouter(prefix="/traces", dependencies=[Depends(require_operator_scope)])

_ONE_HOUR_S = 3_600


def _default_window() -> tuple[int, int]:
    end_s = int(time.time())
    return end_s - _ONE_HOUR_S, end_s


def _to_s(dt: datetime | None) -> int | None:
    return int(dt.timestamp()) if dt is not None else None


async def _run_search(
    query_service: TraceQueryService,
    *,
    service: str | None,
    status: str | None,
    min_duration_ms: int | None,
    tenant_id: str | None,
    q: str | None,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> TraceSearchResponse:
    default_start, default_end = _default_window()
    summaries = await query_service.search(
        service=service,
        status=status,
        min_duration_ms=min_duration_ms,
        tenant_id=tenant_id,
        query_text=q,
        start_s=_to_s(start) or default_start,
        end_s=_to_s(end) or default_end,
        limit=limit,
    )
    items = [TraceSummaryResponse.from_summary(s) for s in summaries]
    return TraceSearchResponse(items=items, count=len(items))


@router.get(
    "/search",
    tags=["Traces — Search"],
    summary="Search traces",
    response_model=TraceSearchResponse,
)
async def search_traces(
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
    service: str | None = Query(default=None, description="Filter by resource.service.name"),
    status: str | None = Query(default=None, description="ok | error | unset"),
    min_duration_ms: int | None = Query(default=None, ge=0),
    tenant_id: str | None = Query(
        default=None, description="Currently a no-op — see TODO.md Decision #3"
    ),
    q: str | None = Query(
        default=None, description="Span attribute filter: key=value[,key2=value2]"
    ),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
) -> TraceSearchResponse:
    return await _run_search(
        query_service,
        service=service,
        status=status,
        min_duration_ms=min_duration_ms,
        tenant_id=tenant_id,
        q=q,
        start=start,
        end=end,
        limit=limit,
    )


@router.get(
    "/service/{service}",
    tags=["Traces — Search"],
    summary="Traces for a specific service",
    response_model=TraceSearchResponse,
)
async def traces_by_service(
    service: str,
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
    status: str | None = Query(default=None),
    min_duration_ms: int | None = Query(default=None, ge=0),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
) -> TraceSearchResponse:
    return await _run_search(
        query_service,
        service=service,
        status=status,
        min_duration_ms=min_duration_ms,
        tenant_id=None,
        q=None,
        start=start,
        end=end,
        limit=limit,
    )


@router.get(
    "/errors",
    tags=["Traces — Search"],
    summary="Traces containing an error span",
    response_model=TraceSearchResponse,
)
async def error_traces(
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
    service: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
) -> TraceSearchResponse:
    return await _run_search(
        query_service,
        service=service,
        status="error",
        min_duration_ms=None,
        tenant_id=None,
        q=None,
        start=start,
        end=end,
        limit=limit,
    )


@router.get(
    "/slow",
    tags=["Traces — Search"],
    summary="Traces slower than a duration threshold",
    response_model=TraceSearchResponse,
)
async def slow_traces(
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
    service: str | None = Query(default=None),
    min_duration_ms: int = Query(default=500, ge=0),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
) -> TraceSearchResponse:
    return await _run_search(
        query_service,
        service=service,
        status=None,
        min_duration_ms=min_duration_ms,
        tenant_id=None,
        q=None,
        start=start,
        end=end,
        limit=limit,
    )


@router.post(
    "/export",
    tags=["Traces — Export"],
    summary="Stream a filtered trace range as NDJSON",
)
async def export_traces(
    export_service: Annotated[TraceExportService, Depends(get_export_service)],
    service: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_duration_ms: int | None = Query(default=None, ge=0),
    tenant_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
    full: bool = Query(
        default=False,
        description="Fetch full span trees, not just summaries — capped lower (see service)",
    ),
) -> StreamingResponse:
    default_start, default_end = _default_window()
    stream = export_service.export_ndjson(
        service=service,
        status=status,
        min_duration_ms=min_duration_ms,
        tenant_id=tenant_id,
        query_text=q,
        start_s=_to_s(start) or default_start,
        end_s=_to_s(end) or default_end,
        limit=limit,
        full=full,
    )
    return StreamingResponse(stream, media_type="application/x-ndjson")


@router.get(
    "/{trace_id}",
    tags=["Traces — Search"],
    summary="Fetch a full trace by id",
    response_model=TraceResponse,
)
async def get_trace(
    trace_id: str,
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
) -> TraceResponse:
    trace = await query_service.get_trace(trace_id)
    return TraceResponse.from_trace(trace)


@router.get(
    "/{trace_id}/timeline",
    tags=["Traces — Search"],
    summary="Fetch a trace reshaped into a chronological timeline",
    response_model=TimelineResponse,
)
async def get_trace_timeline(
    trace_id: str,
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
) -> TimelineResponse:
    trace = await query_service.get_trace(trace_id)
    return TimelineResponse.from_trace(trace)


@router.get(
    "/{trace_id}/spans",
    tags=["Traces — Search"],
    summary="Fetch the flat span list for a trace",
    response_model=SpansResponse,
)
async def get_trace_spans(
    trace_id: str,
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
) -> SpansResponse:
    trace = await query_service.get_trace(trace_id)
    return SpansResponse.from_trace(trace)


@router.delete(
    "/{trace_id}",
    tags=["Traces — Search"],
    summary="Not supported — Tempo has no per-trace delete (see TODO.md Decision #4)",
    status_code=501,
)
async def delete_trace(trace_id: str) -> dict[str, str]:
    return {
        "detail": (
            "Per-trace delete is not supported: Tempo has no concept of deleting "
            "a single trace. Retention is bulk and time-window based "
            "(tempo.yml compactor.compaction.block_retention). If this is for a "
            "GDPR-style erasure request, that needs a coarse, filter-based "
            "erasure process instead (see services/DistributedTracing/TODO.md "
            "Decision #4)."
        )
    }
