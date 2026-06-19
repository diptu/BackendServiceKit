"""
JWT context middleware.

Decodes the Bearer token (if any) once, at the edge, and stashes the claims
on `request.state.jwt_claims`. `app.core.security.is_authenticated` reuses
them when present instead of decoding the token a second time per request —
a pure performance optimization with an unchanged external contract: this
middleware never raises. An absent/invalid/wrong-type token simply leaves
`request.state.jwt_claims` unset, and the existing `is_authenticated`
dependency decodes (and rejects) the token itself exactly as it did before
this middleware existed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.token_blacklist import is_token_revoked

_NextCall = Callable[[Request], Awaitable[Response]]
_BEARER_PREFIX = "bearer "


class JWTContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: _NextCall) -> Response:
        request.state.jwt_claims = None

        header = request.headers.get("authorization", "")
        if header.lower().startswith(_BEARER_PREFIX):
            token = header[len(_BEARER_PREFIX) :]
            request.state.jwt_claims = await _decode_access_token(token)

        return await call_next(request)


async def _decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("sub") is None or payload.get("type") != "access":
        return None

    # A blacklisted (logged-out) jti or a token issued before the account's
    # last password change must not be cached here as "authenticated" —
    # otherwise is_authenticated's cached-claims fast path would let it
    # through unchecked.
    if await is_token_revoked(payload):
        return None

    return payload
