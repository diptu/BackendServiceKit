"""X-Request-ID middleware — injects/propagates request IDs."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import _request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        req_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = _request_id_var.set(req_id)
        request.state.request_id = req_id
        try:
            response: Response = await call_next(request)  # type: ignore[arg-type]
        finally:
            _request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = req_id
        return response
