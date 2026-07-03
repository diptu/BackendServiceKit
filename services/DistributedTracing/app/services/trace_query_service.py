"""Read-path business logic: turns validated filters into Tempo queries."""

from __future__ import annotations

from app.domain.exceptions import TraceNotFoundError
from app.domain.span import Trace, TraceSummary
from app.infrastructure.tempo.tempo_client import TempoClient
from app.repositories.trace_repository import build_traceql, parse_search_results, parse_trace


class TraceQueryService:
    def __init__(self, tempo_client: TempoClient) -> None:
        self._tempo = tempo_client

    async def get_trace(self, trace_id: str) -> Trace:
        data = await self._tempo.trace_by_id(trace_id)
        if data is None:
            raise TraceNotFoundError(
                f"No trace found for id {trace_id!r} (bad id, or outside the retention window)."
            )
        trace = parse_trace(data, trace_id=trace_id)
        if not trace.spans:
            raise TraceNotFoundError(
                f"No trace found for id {trace_id!r} (bad id, or outside the retention window)."
            )
        return trace

    async def search(
        self,
        *,
        service: str | None = None,
        status: str | None = None,
        min_duration_ms: int | None = None,
        tenant_id: str | None = None,
        query_text: str | None = None,
        start_s: int,
        end_s: int,
        limit: int = 20,
    ) -> list[TraceSummary]:
        traceql = build_traceql(
            service=service,
            status=status,
            min_duration_ms=min_duration_ms,
            tenant_id=tenant_id,
            query_text=query_text,
        )
        data = await self._tempo.search(traceql=traceql, start=start_s, end=end_s, limit=limit)
        return parse_search_results(data)
