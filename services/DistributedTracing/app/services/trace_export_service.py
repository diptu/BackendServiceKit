"""Streaming NDJSON export — synchronous, no worker infra (see TODO.md Phase 7)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from app.domain.exceptions import TraceNotFoundError
from app.services.trace_query_service import TraceQueryService

_MAX_SUMMARY_ITEMS = 500
# Fetching full span trees means one extra Tempo call per result — cap harder.
_MAX_FULL_ITEMS = 50


class TraceExportService:
    def __init__(self, query_service: TraceQueryService) -> None:
        self._query_service = query_service

    async def export_ndjson(
        self,
        *,
        service: str | None,
        status: str | None,
        min_duration_ms: int | None,
        tenant_id: str | None,
        query_text: str | None,
        start_s: int,
        end_s: int,
        limit: int,
        full: bool,
    ) -> AsyncIterator[bytes]:
        cap = _MAX_FULL_ITEMS if full else _MAX_SUMMARY_ITEMS
        summaries = await self._query_service.search(
            service=service,
            status=status,
            min_duration_ms=min_duration_ms,
            tenant_id=tenant_id,
            query_text=query_text,
            start_s=start_s,
            end_s=end_s,
            limit=min(limit, cap),
        )
        for summary in summaries:
            if full:
                try:
                    trace = await self._query_service.get_trace(summary.trace_id)
                except TraceNotFoundError:
                    continue
                payload = {
                    "trace_id": trace.trace_id,
                    "duration_ns": trace.duration_ns,
                    "service_names": sorted(trace.service_names),
                    "spans": [
                        {
                            "span_id": s.span_id,
                            "parent_span_id": s.parent_span_id,
                            "name": s.name,
                            "service": s.service,
                            "start_ns": s.start_ns,
                            "duration_ns": s.duration_ns,
                            "status": s.status,
                        }
                        for s in trace.spans
                    ],
                }
            else:
                payload = {
                    "trace_id": summary.trace_id,
                    "root_service_name": summary.root_service_name,
                    "root_trace_name": summary.root_trace_name,
                    "start_ns": summary.start_ns,
                    "duration_ms": summary.duration_ms,
                }
            yield (json.dumps(payload, default=str) + "\n").encode("utf-8")
