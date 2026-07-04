"""Business logic for the Traces domain — composes TempoClient +
trace_repository. This is the plain service class the Observability
domain imports directly in-process (TODO.md Decision #4)."""

from __future__ import annotations

import time

from app.domains.tracing.infrastructure.tempo_client import TempoClient
from app.domains.tracing.repositories.trace_repository import (
    Span,
    TraceSummary,
    parse_full_trace_response,
    parse_search_response,
)


class TraceQueryService:
    def __init__(self, tempo_client: TempoClient) -> None:
        self._tempo = tempo_client

    async def search(
        self, *, query: str = "", minutes: float = 15.0, limit: int = 20
    ) -> list[TraceSummary]:
        now = int(time.time())
        start = now - int(minutes * 60)
        raw = await self._tempo.search(query=query, start_s=start, end_s=now, limit=limit)
        if raw is None:
            return []
        return parse_search_response(raw)

    async def count_errors(self, *, minutes: float = 15.0) -> int | None:
        now = int(time.time())
        start = now - int(minutes * 60)
        raw = await self._tempo.search(query="{status=error}", start_s=start, end_s=now, limit=1000)
        if raw is None:
            return None
        return len(parse_search_response(raw))

    async def get_spans(self, trace_id: str) -> list[Span]:
        raw = await self._tempo.get_trace(trace_id)
        if raw is None:
            return []
        return parse_full_trace_response(raw)

    async def recent_traces_with_spans(
        self, *, minutes: float = 15.0, limit: int = 20
    ) -> list[list[Span]] | None:
        """Search for recent traces, then fetch full span data for each —
        used by the Observability domain's topology mining (Decision #2).
        Returns None only when the initial search itself is unreachable,
        distinguishing "Tempo is down" from "no traces in this window"."""
        now = int(time.time())
        start = now - int(minutes * 60)
        raw = await self._tempo.search(start_s=start, end_s=now, limit=limit)
        if raw is None:
            return None
        summaries = parse_search_response(raw)
        results = []
        for summary in summaries:
            spans = await self.get_spans(summary.trace_id)
            if spans:
                results.append(spans)
        return results
