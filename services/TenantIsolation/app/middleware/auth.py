"""JWT Bearer Token authentication — applied as a FastAPI dependency."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def verify_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Validate JWT bearer token. No-op when jwt_auth_enabled=False."""
    if not settings.jwt_auth_enabled:
        return

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    try:
        from jose import jwt  # type: ignore[import-untyped]

        jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except Exception:
        logger.warning("jwt_validation_failed", extra={"path": str(request.url.path)})
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
