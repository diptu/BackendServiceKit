"""Rate limiting via slowapi — keyed by tenant when known, else caller IP.

Unlike Tenent's rate_limit.py (wired as middleware but never applied to any
route with @limiter.limit(...)), this service actually decorates /login —
brute-force protection on the credential-verification endpoint is the one
place this repo's own Authentication skill calls out as non-negotiable.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def _get_tenant_key(request: Request) -> str:
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return f"tenant:{tenant_id}"
    return get_remote_address(request) or "unknown"


limiter = Limiter(
    key_func=_get_tenant_key,
    enabled=settings.rate_limit_enabled,
)
