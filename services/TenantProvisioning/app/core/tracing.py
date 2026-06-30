"""OpenTelemetry tracing setup — degrades gracefully when SDK not configured."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


def configure_tracing(
    *,
    service_name: str,
    endpoint: str,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    try:
        from opentelemetry import trace  # type: ignore[import-untyped]
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-untyped]
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-untyped]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-untyped]
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-untyped]

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("otel_tracing_configured", extra={"endpoint": endpoint, "service": service_name})
    except Exception as exc:
        logger.warning("otel_configure_failed", extra={"error": str(exc)})


def get_tracer(name: str) -> Any:
    try:
        from opentelemetry import trace  # type: ignore[import-untyped]
        return trace.get_tracer(name)
    except Exception:
        return _NoopTracer()


@contextmanager
def traced_step(tracer: Any, step_name: str) -> Generator[None, None, None]:
    """Context manager for a single provisioning step span."""
    try:
        with tracer.start_as_current_span(f"provisioning.step.{step_name}"):
            yield
    except Exception:
        yield


class _NoopTracer:
    def start_as_current_span(self, name: str) -> Any:
        return _NoopSpan()


class _NoopSpan:
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *_: object) -> None:
        pass
