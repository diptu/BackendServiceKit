"""Translates domain-level filters into TraceQL and parses Tempo's response back.

This is the only place TraceQL syntax is constructed — no other module
should build a query string by hand (same rule Logging applies to LogQL in
`services/Logging/app/repositories/log_repository.py`).

Response shapes handled here (verify against a real Tempo container before
trusting blindly — see TODO.md Phase 11):
  - `GET /api/search` → `{"traces": [{"traceID", "rootServiceName",
    "rootTraceName", "startTimeUnixNano", "durationMs"}, ...]}`
  - `GET /api/traces/{id}` → OTLP-JSON trace data. Tempo has used the field
    name `batches` (legacy Jaeger-compatible naming) for this list even
    though the objects inside are OTLP `ResourceSpans`-shaped; this parser
    accepts both `batches` and the OTLP-native `resourceSpans` key, and both
    `scopeSpans` and the older `instrumentationLibrarySpans` key, so it
    doesn't silently return an empty trace if Tempo's actual wire format
    differs from what was assumed at write time.

Verified against a real `grafana/tempo:2.5.0` container (push a span via its
OTLP HTTP receiver, then fetch it back) — this caught a real, non-obvious
encoding mismatch between the two endpoints: `/api/search`'s `traceID` /
`spanID` fields are plain hex strings, but `/api/traces/{id}`'s nested
`spanId` / `parentSpanId` fields are base64-encoded bytes (standard OTLP-JSON
proto encoding for a `bytes` field) — NOT hex, even though they represent the
same span id. `_decode_span_id` below converts the latter to the same hex
convention as `/api/search`, the URL path parameter, and every trace-viewer
UI (Grafana/Jaeger) — without it, a span's `span_id` in this service's
responses would silently be unusable for cross-referencing against
`/api/search` results or the `{trace_id}` URL a caller already has.
"""

from __future__ import annotations

import base64
from typing import Any

from app.domain.exceptions import InvalidTraceQLError
from app.domain.span import Span, Trace, TraceSummary

_VALID_STATUSES = frozenset({"ok", "error", "unset"})

_STATUS_CODE_MAP = {
    "STATUS_CODE_OK": "ok",
    "STATUS_CODE_ERROR": "error",
    "STATUS_CODE_UNSET": "unset",
}


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_traceql(
    *,
    service: str | None = None,
    status: str | None = None,
    min_duration_ms: int | None = None,
    tenant_id: str | None = None,
    query_text: str | None = None,
) -> str:
    """Build a TraceQL span-set selector for the given filters.

    `tenant_id` is a forward-compatible no-op today — no span carries a
    `tenant.id` attribute yet (see TODO.md Decision #3). The filter is built
    anyway so it starts working the moment that attribute is wired in
    upstream, without needing a second change here.
    """
    clauses: list[str] = []
    if service:
        clauses.append(f'resource.service.name="{_escape(service)}"')
    if status:
        if status not in _VALID_STATUSES:
            raise InvalidTraceQLError(
                f"status must be one of {sorted(_VALID_STATUSES)}, got {status!r}"
            )
        clauses.append(f"status={status}")
    if min_duration_ms is not None:
        clauses.append(f"duration>{min_duration_ms}ms")
    if tenant_id:
        clauses.append(f'span."tenant.id"="{_escape(tenant_id)}"')
    if query_text:
        for pair in query_text.split(","):
            if "=" not in pair:
                raise InvalidTraceQLError(f"Invalid q filter {pair!r}, expected key=value")
            key, value = pair.split("=", 1)
            key, value = key.strip(), value.strip()
            if not key:
                raise InvalidTraceQLError(f"Invalid q filter {pair!r}, empty key")
            clauses.append(f'span.{key}="{_escape(value)}"')

    if not clauses:
        return "{}"
    return "{ " + " && ".join(clauses) + " }"


def parse_search_results(data: dict[str, Any]) -> list[TraceSummary]:
    """Parse a Tempo `/api/search` response body into `TraceSummary` objects."""
    results = data.get("traces") or []
    summaries = [
        TraceSummary(
            trace_id=item.get("traceID", ""),
            root_service_name=item.get("rootServiceName"),
            root_trace_name=item.get("rootTraceName"),
            start_ns=int(item.get("startTimeUnixNano", 0) or 0),
            duration_ms=float(item.get("durationMs", 0) or 0),
        )
        for item in results
    ]
    summaries.sort(key=lambda s: s.start_ns, reverse=True)
    return summaries


def parse_trace(data: dict[str, Any], *, trace_id: str) -> Trace:
    """Parse a Tempo `/api/traces/{id}` response body into a `Trace` object."""
    spans: list[Span] = []
    resource_spans = data.get("batches") or data.get("resourceSpans") or []
    for rs in resource_spans:
        service_name = _extract_service_name(rs.get("resource", {}) or {})
        scope_spans = rs.get("scopeSpans") or rs.get("instrumentationLibrarySpans") or []
        for ss in scope_spans:
            for raw_span in ss.get("spans", []) or []:
                spans.append(_parse_span(raw_span, service_name))
    return Trace(trace_id=trace_id, spans=spans)


def _extract_service_name(resource: dict[str, Any]) -> str | None:
    for attr in resource.get("attributes", []) or []:
        if attr.get("key") == "service.name":
            value = _attr_value(attr.get("value", {}) or {})
            return str(value) if value is not None else None
    return None


def _attr_value(value: dict[str, Any]) -> Any:
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        return int(value["intValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "boolValue" in value:
        return bool(value["boolValue"])
    if "arrayValue" in value:
        return [_attr_value(v) for v in value["arrayValue"].get("values", [])]
    return None


def _decode_span_id(value: str | None) -> str | None:
    """Convert a base64-encoded OTLP-JSON `bytes` field to the conventional hex form.

    See the module docstring — `/api/traces/{id}` returns spanId/parentSpanId
    base64-encoded, unlike every other place a span/trace id shows up in this
    service (URL paths, `/api/search` results).
    """
    if not value:
        return None
    try:
        return base64.b64decode(value).hex()
    except (ValueError, TypeError):
        # Already hex, or some other Tempo version encodes it differently —
        # fall back to the raw value rather than dropping it.
        return value


def _parse_span(raw: dict[str, Any], service_name: str | None) -> Span:
    attributes = {
        attr["key"]: _attr_value(attr.get("value", {}) or {})
        for attr in raw.get("attributes", []) or []
        if "key" in attr
    }
    status_code = (raw.get("status") or {}).get("code", "STATUS_CODE_UNSET")
    return Span(
        span_id=_decode_span_id(raw.get("spanId")) or "",
        parent_span_id=_decode_span_id(raw.get("parentSpanId")),
        name=raw.get("name", ""),
        service=service_name,
        start_ns=int(raw.get("startTimeUnixNano", 0) or 0),
        end_ns=int(raw.get("endTimeUnixNano", 0) or 0),
        status=_STATUS_CODE_MAP.get(status_code, "unset"),
        attributes=attributes,
    )
