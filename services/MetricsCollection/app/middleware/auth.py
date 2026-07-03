"""JWT Bearer Token authentication — copied from Logging/DistributedTracing verbatim.

Same library, same settings fields, same no-op-when-disabled behavior, so
operators configuring auth across services don't have to learn a second
convention for this one.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def verify_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any]:
    """Validate JWT bearer token and return its claims.

    No-op (returns an empty claim set) when jwt_auth_enabled=False.
    """
    if not settings.jwt_auth_enabled:
        return {}

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    try:
        from jose import jwt  # type: ignore[import-untyped]

        claims: dict[str, Any] = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return claims
    except Exception:
        logger.warning("jwt_validation_failed", extra={"path": str(request.url.path)})
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
