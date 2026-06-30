"""Starlette middleware that records RED metrics via prometheus-client."""

from __future__ import annotations

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code", "service"],
)

_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "service"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

_SKIP_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/metrics", "/ready"})


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Records http_requests_total and http_request_duration_seconds per request."""

    def __init__(self, app: object, service_name: str = "unknown") -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._service = service_name

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)  # type: ignore[operator,misc]
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator,misc]
        duration = time.perf_counter() - start
        path = request.url.path
        _REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status_code=str(response.status_code),
            service=self._service,
        ).inc()
        _REQUEST_LATENCY.labels(
            method=request.method,
            path=path,
            service=self._service,
        ).observe(duration)
        return response
