"""Starlette middleware — structured JSON log per completed request."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_SKIP_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/metrics", "/ready"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one JSON line per request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)  # type: ignore[operator,misc]
        start = time.perf_counter()
        response: Response = await call_next(request)  # type: ignore[operator,misc]
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request.headers.get("X-Request-ID"),
            },
        )
        return response
