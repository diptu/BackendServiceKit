"""W3C Trace Context propagator setup."""

from __future__ import annotations

from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def configure_propagator() -> None:
    """Install W3C traceparent + tracestate + baggage as global propagators.

    Must be called after configure_tracer(). Kong injects traceparent at the
    edge; this ensures all downstream FastAPI services propagate the same context.
    """
    set_global_textmap(
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
                W3CBaggagePropagator(),
            ]
        )
    )
