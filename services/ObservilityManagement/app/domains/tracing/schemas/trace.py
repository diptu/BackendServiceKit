"""Request/response schemas for the Traces domain."""

from __future__ import annotations

from app.core.schema_base import APIModel
from app.domains.tracing.repositories.trace_repository import TraceSummary


class TraceSummaryResponse(APIModel):
    trace_id: str
    root_service: str
    root_name: str
    start_time: str
    duration_ms: int

    @classmethod
    def from_domain(cls, summary: TraceSummary) -> "TraceSummaryResponse":
        return cls(
            trace_id=summary.trace_id,
            root_service=summary.root_service,
            root_name=summary.root_name,
            start_time=summary.start_time,
            duration_ms=summary.duration_ms,
        )


class TraceSearchResponse(APIModel):
    items: list[TraceSummaryResponse]
    count: int
