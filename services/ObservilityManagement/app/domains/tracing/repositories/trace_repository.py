"""Parses Tempo's real search and full-trace responses.

`parse_search_response` handles trace *summaries* (search results — no
span detail). `parse_full_trace_response` handles the real OTLP-JSON shape
Tempo's full-trace endpoint returns — `batches[].resource.attributes`
(service.name lives here) and `batches[].scopeSpans[].spans[]` (span_id/
parent_span_id/name live here). This is the real shape, not a flattened
guess — see `tempo_client.py`'s docstring for why that distinction matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class TraceSummary:
    trace_id: str
    root_service: str
    root_name: str
    start_time: str
    duration_ms: int


@dataclass(frozen=True)
class Span:
    span_id: str
    parent_span_id: str | None
    service_name: str
    name: str


def parse_search_response(raw: dict[str, Any]) -> list[TraceSummary]:
    traces = raw.get("traces")
    if not isinstance(traces, list):
        return []
    results = []
    for item in traces:
        if not isinstance(item, dict):
            continue
        results.append(
            TraceSummary(
                trace_id=str(item.get("traceID", "")),
                root_service=str(item.get("rootServiceName", "")),
                root_name=str(item.get("rootTraceName", "")),
                start_time=_unix_nano_to_iso(item.get("startTimeUnixNano")),
                duration_ms=int(item.get("durationMs") or 0),
            )
        )
    return results


def parse_full_trace_response(raw: dict[str, Any]) -> list[Span]:
    batches = raw.get("batches")
    if not isinstance(batches, list):
        return []

    spans: list[Span] = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        service_name = _extract_service_name(batch.get("resource") or {})
        scope_spans = batch.get("scopeSpans")
        if not isinstance(scope_spans, list):
            continue
        for scope_span in scope_spans:
            if not isinstance(scope_span, dict):
                continue
            raw_spans = scope_span.get("spans")
            if not isinstance(raw_spans, list):
                continue
            for span in raw_spans:
                if not isinstance(span, dict):
                    continue
                spans.append(
                    Span(
                        span_id=str(span.get("spanId", "")),
                        parent_span_id=span.get("parentSpanId") or None,
                        service_name=service_name,
                        name=str(span.get("name", "")),
                    )
                )
    return spans


def _extract_service_name(resource: dict[str, Any]) -> str:
    attributes = resource.get("attributes")
    if not isinstance(attributes, list):
        return "unknown"
    for attr in attributes:
        if not isinstance(attr, dict) or attr.get("key") != "service.name":
            continue
        value = attr.get("value") or {}
        if isinstance(value, dict) and "stringValue" in value:
            return str(value["stringValue"])
    return "unknown"


def _unix_nano_to_iso(ns: Any) -> str:
    try:
        seconds = int(ns) / 1_000_000_000
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(seconds, tz=UTC).isoformat()
