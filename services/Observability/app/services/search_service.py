"""Federated search — TODO.md Decision #5. Dispatches concurrently to
Logging + DistributedTracing, merges results, tagged by source. Metrics
are deliberately excluded — see the Decision's reasoning."""

from __future__ import annotations

import asyncio
from typing import Any

from app.domain.observability import SearchResult
from app.infrastructure.siblings.logging_client import LoggingClient
from app.infrastructure.siblings.tracing_client import TracingClient


class SearchService:
    def __init__(self, logging_client: LoggingClient, tracing_client: TracingClient) -> None:
        self._logging = logging_client
        self._tracing = tracing_client

    async def search(
        self, *, query: str, minutes: float = 15.0, limit: int = 50
    ) -> list[SearchResult]:
        log_body, trace_body = await asyncio.gather(
            self._logging.search(query=query, minutes=minutes, limit=limit),
            self._tracing.search(query=query, minutes=minutes, limit=limit),
        )
        results: list[SearchResult] = []
        results.extend(_log_results(log_body))
        results.extend(_trace_results(trace_body))
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:limit]


def _log_results(body: dict[str, Any] | None) -> list[SearchResult]:
    if not body:
        return []
    items = body.get("items") or body.get("entries") or []
    if not isinstance(items, list):
        return []
    return [
        SearchResult(
            source="log",
            timestamp=str(item.get("timestamp", "")),
            summary=str(item.get("message") or item.get("line") or ""),
            raw=item,
        )
        for item in items
        if isinstance(item, dict)
    ]


def _trace_results(body: dict[str, Any] | None) -> list[SearchResult]:
    if not body:
        return []
    items = body.get("items") or body.get("traces") or []
    if not isinstance(items, list):
        return []
    return [
        SearchResult(
            source="trace",
            timestamp=str(item.get("timestamp") or item.get("start_time") or ""),
            summary=str(item.get("root_service") or item.get("trace_id") or ""),
            raw=item,
        )
        for item in items
        if isinstance(item, dict)
    ]
