"""OTLP exporter factories for traces and metrics."""

from __future__ import annotations

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def create_otlp_span_exporter(endpoint: str) -> OTLPSpanExporter:
    """OTLP gRPC span exporter — insecure, 10 s timeout."""
    return OTLPSpanExporter(endpoint=endpoint, insecure=True, timeout=10)


def create_otlp_metric_exporter(endpoint: str) -> OTLPMetricExporter:
    """OTLP gRPC metric exporter — insecure, 10 s timeout."""
    return OTLPMetricExporter(endpoint=endpoint, insecure=True, timeout=10)
