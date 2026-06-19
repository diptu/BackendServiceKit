"""
Baseline security response headers (defense-in-depth, not a substitute
for CSP/input validation done elsewhere).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

_NextCall = Callable[[Request], Awaitable[Response]]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: _NextCall) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Only advertise HSTS when actually serving over HTTPS — reuses the
        # existing COOKIE_SECURE flag rather than inventing a second one.
        if settings.COOKIE_SECURE:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={settings.HSTS_MAX_AGE_SECONDS}; includeSubDomains"
            )
        return response
