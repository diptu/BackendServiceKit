"""Operator-only access control — one shared `require_operator_scope`
instead of seven copies. Same uniform single-tier model every merged
service used individually."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends

from app.core.config import settings
from app.core.exceptions import NotAnOperatorError
from app.middleware.auth import verify_token

PLATFORM_ADMIN_ROLE = "platform-admin"


async def require_operator_scope(
    claims: Annotated[dict[str, Any], Depends(verify_token)],
) -> None:
    """Gates every operator-only endpoint across every domain. No-op when
    jwt_auth_enabled=False."""
    if not settings.jwt_auth_enabled:
        return
    roles = claims.get("roles") or []
    if PLATFORM_ADMIN_ROLE not in roles:
        raise NotAnOperatorError()
