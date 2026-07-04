"""Business logic for the Logs domain — composes LokiClient +
log_repository. This is the plain service class the Observability domain
imports directly in-process (TODO.md Decision #4) instead of going through
an HTTP sibling client."""

from __future__ import annotations

import time

from app.domains.logging.infrastructure.loki_client import LokiClient
from app.domains.logging.repositories.log_repository import (
    LogEntry,
    build_logql_query,
    parse_query_range_response,
)


class LogQueryService:
    def __init__(self, loki_client: LokiClient) -> None:
        self._loki = loki_client

    async def search(
        self,
        *,
        query: str | None = None,
        service: str | None = None,
        level: str | None = None,
        text: str | None = None,
        minutes: float = 15.0,
        limit: int = 100,
    ) -> list[LogEntry]:
        logql = query or build_logql_query(service=service, level=level, text=text)
        now_ns = time.time_ns()
        start_ns = now_ns - int(minutes * 60 * 1_000_000_000)
        raw = await self._loki.query_range(
            query=logql, start_ns=start_ns, end_ns=now_ns, limit=limit
        )
        if raw is None:
            return []
        return parse_query_range_response(raw)

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        raw = await self._loki.query_range(
            query=build_logql_query(level="error"),
            start_ns=time.time_ns() - int(minutes * 60 * 1_000_000_000),
            end_ns=time.time_ns(),
            limit=1000,
        )
        if raw is None:
            return None
        return len(parse_query_range_response(raw))
