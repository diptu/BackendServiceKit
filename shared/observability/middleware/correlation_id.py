"""Starlette middleware — generates or propagates X-Request-ID per request."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Reads X-Request-ID from the request; generates a UUID4 if absent.

    Injects the ID into the response headers so clients can correlate
    requests with log entries and traces.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get(_HEADER) or str(uuid.uuid4())
        response: Response = await call_next(request)  # type: ignore[operator,misc]
        response.headers[_HEADER] = request_id
        return response
