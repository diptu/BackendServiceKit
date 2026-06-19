"""
HTTP-level Prometheus metrics (Golden Signals: traffic, errors, latency).

A deliberately small surface — request count and latency by method/path/
status — rather than re-deriving business metrics already covered by the
audit log (see app.audit.events). Scraped via GET /metrics (see app.main).
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "iam_http_requests_total",
    "Total HTTP requests handled by the IAM service.",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "iam_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
