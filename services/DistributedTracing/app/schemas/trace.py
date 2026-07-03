"""Request/response schemas for the traces API."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.domain.span import Span, Trace, TraceSummary
from app.schemas.base import APIModel


class SpanResponse(APIModel):
    span_id: str
    parent_span_id: str | None
    name: str
    service: str | None
    start_ns: int
    duration_ns: int
    status: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_span(cls, span: Span) -> "SpanResponse":
        return cls(
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            name=span.name,
            service=span.service,
            start_ns=span.start_ns,
            duration_ns=span.duration_ns,
            status=span.status,
            attributes=span.attributes,
        )


class TraceResponse(APIModel):
    trace_id: str
    root_span_id: str | None
    duration_ns: int
    service_names: list[str]
    spans: list[SpanResponse]

    @classmethod
    def from_trace(cls, trace: Trace) -> "TraceResponse":
        root = trace.root_span
        return cls(
            trace_id=trace.trace_id,
            root_span_id=root.span_id if root else None,
            duration_ns=trace.duration_ns,
            service_names=sorted(trace.service_names),
            spans=[SpanResponse.from_span(s) for s in trace.spans],
        )


class TimelineEntryResponse(APIModel):
    span_id: str
    parent_span_id: str | None
    name: str
    service: str | None
    relative_start_ms: float
    duration_ms: float
    status: str


class TimelineResponse(APIModel):
    trace_id: str
    total_duration_ms: float
    entries: list[TimelineEntryResponse]

    @classmethod
    def from_trace(cls, trace: Trace) -> "TimelineResponse":
        base_ns = trace.start_ns
        ordered = sorted(trace.spans, key=lambda s: s.start_ns)
        entries = [
            TimelineEntryResponse(
                span_id=s.span_id,
                parent_span_id=s.parent_span_id,
                name=s.name,
                service=s.service,
                relative_start_ms=(s.start_ns - base_ns) / 1_000_000,
                duration_ms=s.duration_ns / 1_000_000,
                status=s.status,
            )
            for s in ordered
        ]
        return cls(
            trace_id=trace.trace_id,
            total_duration_ms=trace.duration_ns / 1_000_000,
            entries=entries,
        )


class SpansResponse(APIModel):
    trace_id: str
    spans: list[SpanResponse]

    @classmethod
    def from_trace(cls, trace: Trace) -> "SpansResponse":
        return cls(trace_id=trace.trace_id, spans=[SpanResponse.from_span(s) for s in trace.spans])


class TraceSummaryResponse(APIModel):
    trace_id: str
    root_service_name: str | None
    root_trace_name: str | None
    start_ns: int
    duration_ms: float

    @classmethod
    def from_summary(cls, summary: TraceSummary) -> "TraceSummaryResponse":
        return cls(
            trace_id=summary.trace_id,
            root_service_name=summary.root_service_name,
            root_trace_name=summary.root_trace_name,
            start_ns=summary.start_ns,
            duration_ms=summary.duration_ms,
        )


class TraceSearchResponse(APIModel):
    items: list[TraceSummaryResponse]
    count: int
