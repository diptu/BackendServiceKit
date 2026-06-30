"""FastAPI auto-instrumentation helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from opentelemetry.sdk.trace import TracerProvider


def instrument_fastapi(
    app: FastAPI,
    *,
    tracer_provider: TracerProvider | None = None,
) -> None:
    """Instrument a FastAPI application with OTel tracing.

    Attaches span creation to every route handler and records HTTP attributes
    (method, route, status code) automatically. Call after configure_tracer().
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore[import]

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
