"""TracerProvider factory — configure once at service startup."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracer(
    service_name: str,
    endpoint: str,
    environment: str = "development",
) -> TracerProvider:
    """Create and install a TracerProvider backed by OTLP gRPC export.

    Call once at application startup. The provider is set as the global
    provider so all downstream instrumentors pick it up automatically.
    """
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: environment,
        }
    )
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True, timeout=10)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str) -> trace.Tracer:
    """Convenience wrapper around the global tracer provider."""
    return trace.get_tracer(name)
