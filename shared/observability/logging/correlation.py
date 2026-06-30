"""Helpers for reading trace context from the active OTel span."""

from __future__ import annotations


def get_trace_context() -> dict[str, str | None]:
    """Return trace_id and span_id from the current active span.

    Returns None values when there is no active span (e.g., outside a request).
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
    except Exception:
        pass
    return {"trace_id": None, "span_id": None}
