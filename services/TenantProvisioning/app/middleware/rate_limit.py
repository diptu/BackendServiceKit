"""Per-tenant rate limiting via slowapi."""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter  # type: ignore[import-untyped]
from slowapi.util import get_remote_address  # type: ignore[import-untyped]

from app.core.config import settings


def _get_tenant_key(request: Request) -> str:
    tenant_id = request.path_params.get("tenant_id")
    if tenant_id:
        return f"tenant:{tenant_id}"
    return get_remote_address(request) or "unknown"


limiter = Limiter(
    key_func=_get_tenant_key,
    enabled=settings.rate_limit_enabled,
)
