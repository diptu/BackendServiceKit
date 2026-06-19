from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

_NextCall = Callable[[Request], Awaitable[Response]]


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: _NextCall) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Use the matched route's path *template* (e.g.
        # "/api/v1/organizations/{organization_id}"), not the raw URL, to
        # keep the metric's cardinality bounded — a raw path would mint a
        # new label series per UUID. Starlette sets `scope["route"]` during
        # routing, which has already run by the time call_next() returns.
        route = request.scope.get("route")
        path = route.path if route is not None else "unmatched"

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method, path=path, status_code=response.status_code
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path).observe(
            duration
        )

        return response
