"""The logs API — read (search/get), ingest (escape hatch), export.

Route registration order matters: literal-prefix paths (`/search`, `/tenant/*`,
`/service/*`, `/user/*`, `/bulk`, `/export`) MUST be declared before the
dynamic `/{id}` route below them, or FastAPI would match e.g. `/logs/search`
as `/logs/{id}` with `id="search"`.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.v1.dependencies import (
    CallerScope,
    check_tenant_access,
    get_export_service,
    get_ingest_service,
    get_query_service,
    require_platform_admin,
    require_tenant_scope,
)
from app.schemas.log import (
    IngestAcceptedResponse,
    LogEntryCreate,
    LogEntryResponse,
    LogSearchResponse,
    LogsBulkCreate,
)
from app.services.log_export_service import LogExportService
from app.services.log_ingest_service import LogIngestService
from app.services.log_query_service import LogQueryService

router = APIRouter(prefix="/logs")

_ONE_HOUR_NS = 3_600_000_000_000


def _default_window() -> tuple[int, int]:
    end_ns = time.time_ns()
    return end_ns - _ONE_HOUR_NS, end_ns


def _to_ns(dt: datetime | None) -> int | None:
    return int(dt.timestamp() * 1_000_000_000) if dt is not None else None


async def _run_search(
    query_service: LogQueryService,
    *,
    tenant_id: str | None,
    service: str | None,
    level: str | None,
    user_id: str | None,
    q: str | None,
    start: datetime | None,
    end: datetime | None,
    limit: int,
    cursor: str | None,
) -> LogSearchResponse:
    default_start, default_end = _default_window()
    start_ns = _to_ns(start) or default_start
    end_ns = int(cursor) if cursor else (_to_ns(end) or default_end)

    entries = await query_service.search(
        tenant_id=tenant_id,
        service=service,
        level=level,
        user_id=user_id,
        query_text=q,
        start_ns=start_ns,
        end_ns=end_ns,
        limit=limit,
    )
    items = [
        LogEntryResponse.from_entry(e, log_id=LogQueryService.encode_id_for(e)) for e in entries
    ]
    next_cursor = str(int(entries[-1].timestamp_ns) - 1) if len(entries) == limit else None
    return LogSearchResponse(items=items, count=len(items), cursor=next_cursor)


@router.get(
    "/search",
    tags=["Logs — Search"],
    summary="Search logs within the caller's tenant scope",
    response_model=LogSearchResponse,
)
async def search_logs(
    scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    query_service: Annotated[LogQueryService, Depends(get_query_service)],
    service: str | None = Query(default=None, description="Filter by emitting service name"),
    level: str | None = Query(default=None, description="Filter by log level"),
    user_id: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Free-text line filter (no double quotes)"),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
) -> LogSearchResponse:
    tenant_id = None if scope.is_platform_admin and not scope.tenant_id else scope.tenant_id
    return await _run_search(
        query_service,
        tenant_id=tenant_id,
        service=service,
        level=level,
        user_id=user_id,
        q=q,
        start=start,
        end=end,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/tenant/{tenant_id}",
    tags=["Logs — Search"],
    summary="Logs for a specific tenant",
    response_model=LogSearchResponse,
)
async def logs_by_tenant(
    tenant_id: str,
    scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    query_service: Annotated[LogQueryService, Depends(get_query_service)],
    service: str | None = Query(default=None),
    level: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
) -> LogSearchResponse:
    check_tenant_access(scope, tenant_id)
    return await _run_search(
        query_service,
        tenant_id=tenant_id,
        service=service,
        level=level,
        user_id=None,
        q=None,
        start=start,
        end=end,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/service/{service}",
    tags=["Logs — Search"],
    summary="Logs for a specific service, across all tenants (platform-admin only)",
    response_model=LogSearchResponse,
)
async def logs_by_service(
    service: str,
    _scope: Annotated[CallerScope, Depends(require_platform_admin)],
    query_service: Annotated[LogQueryService, Depends(get_query_service)],
    level: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
) -> LogSearchResponse:
    return await _run_search(
        query_service,
        tenant_id=None,
        service=service,
        level=level,
        user_id=None,
        q=None,
        start=start,
        end=end,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/user/{user_id}",
    tags=["Logs — Search"],
    summary="Logs mentioning a specific user_id, within the caller's tenant scope",
    response_model=LogSearchResponse,
)
async def logs_by_user(
    user_id: str,
    scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    query_service: Annotated[LogQueryService, Depends(get_query_service)],
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = Query(default=None),
) -> LogSearchResponse:
    tenant_id = None if scope.is_platform_admin and not scope.tenant_id else scope.tenant_id
    return await _run_search(
        query_service,
        tenant_id=tenant_id,
        service=None,
        level=None,
        user_id=user_id,
        q=None,
        start=start,
        end=end,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "",
    tags=["Logs — Ingest"],
    summary="Ingest a single log event (escape hatch — see tag description)",
    response_model=IngestAcceptedResponse,
    status_code=202,
)
async def create_log(
    body: LogEntryCreate,
    _scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    ingest_service: Annotated[LogIngestService, Depends(get_ingest_service)],
) -> IngestAcceptedResponse:
    accepted = await ingest_service.ingest_one(body)
    return IngestAcceptedResponse(accepted=accepted)


@router.post(
    "/bulk",
    tags=["Logs — Ingest"],
    summary="Ingest a batch of log events (escape hatch — see tag description)",
    response_model=IngestAcceptedResponse,
    status_code=202,
)
async def create_logs_bulk(
    body: LogsBulkCreate,
    _scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    ingest_service: Annotated[LogIngestService, Depends(get_ingest_service)],
) -> IngestAcceptedResponse:
    accepted = await ingest_service.ingest_bulk(body.items)
    return IngestAcceptedResponse(accepted=accepted)


@router.post(
    "/export",
    tags=["Logs — Export"],
    summary="Stream a filtered log range as NDJSON",
)
async def export_logs(
    scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    export_service: Annotated[LogExportService, Depends(get_export_service)],
    service: str | None = Query(default=None),
    level: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
) -> StreamingResponse:
    default_start, default_end = _default_window()
    tenant_id = None if scope.is_platform_admin and not scope.tenant_id else scope.tenant_id
    stream = export_service.export_ndjson(
        tenant_id=tenant_id,
        service=service,
        level=level,
        user_id=user_id,
        query_text=q,
        start_ns=_to_ns(start) or default_start,
        end_ns=_to_ns(end) or default_end,
    )
    return StreamingResponse(stream, media_type="application/x-ndjson")


@router.get(
    "/{log_id}",
    tags=["Logs — Search"],
    summary="Fetch a single log entry by its synthetic id",
    response_model=LogEntryResponse,
)
async def get_log_by_id(
    log_id: str,
    scope: Annotated[CallerScope, Depends(require_tenant_scope)],
    query_service: Annotated[LogQueryService, Depends(get_query_service)],
) -> LogEntryResponse:
    entry, resolved_id = await query_service.get_by_id(log_id)
    if entry.tenant_id is not None:
        check_tenant_access(scope, entry.tenant_id)
    return LogEntryResponse.from_entry(entry, log_id=resolved_id)


@router.delete(
    "/{log_id}",
    tags=["Logs — Search"],
    summary="Not supported — Loki has no per-line delete (see TODO.md Decision #4)",
    status_code=501,
)
async def delete_log_by_id(
    log_id: str,
    _scope: Annotated[CallerScope, Depends(require_platform_admin)],
) -> dict[str, str]:
    return {
        "detail": (
            "Per-line delete is not supported: Loki has no concept of deleting a "
            "single log line. Retention is bulk and time-window based "
            "(loki-config.yaml table_manager.retention_period). If this is for a "
            "GDPR-style erasure request, use a coarse, filter-based erasure "
            "process instead (see services/Logging/TODO.md Phase 6)."
        )
    }
