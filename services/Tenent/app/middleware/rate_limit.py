"""Per-tenant rate limiting via slowapi."""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter  # type: ignore[import-untyped]
from slowapi.util import get_remote_address  # type: ignore[import-untyped]

from app.core.config import settings


def _get_tenant_key(request: Request) -> str:
    body_tenant = getattr(request.state, "caller_tenant_id", None)
    if body_tenant:
        return f"tenant:{body_tenant}"
    return get_remote_address(request) or "unknown"


limiter = Limiter(
    key_func=_get_tenant_key,
    enabled=settings.rate_limit_enabled,
)
