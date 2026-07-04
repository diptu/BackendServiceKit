"""Logs domain router — mounted at /api/v1/logs (unchanged prefix, see
TODO.md Decision #1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security import require_operator_scope
from app.domains.logging.dependencies import get_log_query_service
from app.domains.logging.schemas.log import LogEntryResponse, LogSearchResponse
from app.domains.logging.services.log_query_service import LogQueryService

router = APIRouter(
    prefix="/logs",
    tags=["Logs"],
    dependencies=[Depends(require_operator_scope)],
)

LogQueryServiceDep = Annotated[LogQueryService, Depends(get_log_query_service)]


@router.get("/search", response_model=LogSearchResponse)
async def search(
    service: LogQueryServiceDep,
    query: Annotated[str | None, Query()] = None,
    log_service: Annotated[str | None, Query(alias="service")] = None,
    level: Annotated[str | None, Query()] = None,
    text: Annotated[str | None, Query()] = None,
    minutes: Annotated[float, Query()] = 15.0,
    limit: Annotated[int, Query(le=1000)] = 100,
) -> LogSearchResponse:
    entries = await service.search(
        query=query, service=log_service, level=level, text=text, minutes=minutes, limit=limit
    )
    items = [LogEntryResponse.from_domain(e) for e in entries]
    return LogSearchResponse(items=items, count=len(items))
