"""Re-export RequestMetricsMiddleware under the middleware namespace."""

from __future__ import annotations

from shared.observability.metrics.middleware import RequestMetricsMiddleware

__all__ = ["RequestMetricsMiddleware"]
