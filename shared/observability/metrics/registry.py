"""Module-level MeterProvider singleton."""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

_provider: MeterProvider | None = None


def get_meter_provider(
    service_name: str = "unknown",
    endpoint: str = "http://otel-collector:4317",
) -> MeterProvider:
    """Return (or create) the global OTLP-backed MeterProvider."""
    global _provider
    if _provider is None:
        resource = Resource.create({SERVICE_NAME: service_name})
        exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30_000)
        _provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(_provider)
    return _provider


def get_meter(name: str) -> metrics.Meter:
    """Convenience wrapper around the global meter provider."""
    return metrics.get_meter(name)
