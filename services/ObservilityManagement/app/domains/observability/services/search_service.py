"""Federated search — in-process fan-out to the Logging + Tracing domains
(TODO.md Decision #5). Metrics are deliberately excluded — PromQL isn't a
free-text search surface the same way."""

from __future__ import annotations

import asyncio

from app.domains.logging.services.log_query_service import LogQueryService
from app.domains.observability.models import SearchResult
from app.domains.observability.services.safe_call import safe_call
from app.domains.tracing.services.trace_query_service import TraceQueryService


class SearchService:
    def __init__(self, log_service: LogQueryService, trace_service: TraceQueryService) -> None:
        self._logs = log_service
        self._traces = trace_service

    async def search(
        self, *, query: str, minutes: float = 15.0, limit: int = 50
    ) -> list[SearchResult]:
        log_entries, trace_summaries = await asyncio.gather(
            safe_call(self._logs.search(text=query, minutes=minutes, limit=limit)),
            safe_call(self._traces.search(query=query, minutes=minutes, limit=limit)),
        )

        results: list[SearchResult] = []
        if log_entries:
            results.extend(
                SearchResult(
                    source="log", timestamp=e.timestamp, summary=e.line, raw={"labels": e.labels}
                )
                for e in log_entries
            )
        if trace_summaries:
            results.extend(
                SearchResult(
                    source="trace",
                    timestamp=s.start_time,
                    summary=s.root_service or s.trace_id,
                    raw={"trace_id": s.trace_id, "root_name": s.root_name},
                )
                for s in trace_summaries
            )

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]
