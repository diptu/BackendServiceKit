"""HTTPX auto-instrumentation — propagates traceparent on outgoing requests."""

from __future__ import annotations


def instrument_httpx() -> None:
    """Instrument all httpx.AsyncClient instances to propagate W3C trace context.

    Adds traceparent/tracestate headers to every outgoing HTTP request so
    downstream services inherit the same trace.
    """
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor  # type: ignore[import]

    HTTPXClientInstrumentor().instrument()
