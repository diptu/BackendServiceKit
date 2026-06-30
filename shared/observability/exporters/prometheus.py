"""Prometheus metric reader factory (direct scrape, bypasses OTel Collector)."""

from __future__ import annotations

from opentelemetry.exporter.prometheus import PrometheusMetricReader  # type: ignore[import]


def create_prometheus_reader() -> PrometheusMetricReader:
    """Prometheus scrape-based MetricReader.

    Use when you want Prometheus to scrape the service directly instead of
    routing metrics through the OTel Collector pipeline.
    """
    return PrometheusMetricReader()
