"""Request-context middleware.

Attaches a unique ``request_id`` to every inbound request:

- Reads ``X-Request-ID`` from the incoming headers (use if the API gateway
  sets it upstream); falls back to a freshly generated UUID.
- Stores the value in a ``contextvars.ContextVar`` so every log record
  emitted during that request automatically includes it.
- Echoes the value back in the ``X-Request-ID`` response header so callers
  can correlate client-side and server-side traces.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Module-level ContextVar — set once per request, readable from any coroutine
# executing in the same context (including logging filters).
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Inject a per-request ID into the context and response headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = req_id
        return response
