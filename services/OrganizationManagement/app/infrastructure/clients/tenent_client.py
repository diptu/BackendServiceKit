"""HTTP client that validates a tenant_id against Tenent at organization-creation time.

Deliberately synchronous and fail-fast — unlike the fire-and-log pattern Tenent
itself uses when notifying TenantProvisioning (a side effect that's allowed to be
best-effort), creating an organization under a tenant_id that doesn't exist is a
real correctness error the caller needs to see, not something to silently ignore.
No local copy of tenant data is kept — this is a point-in-time existence check,
not a projection.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from app.core.config import settings
from app.domain.exceptions import TenantNotFoundError, TenantServiceUnavailableError


class TenentClient:
    async def assert_tenant_exists(self, tenant_id: UUID) -> None:
        url = f"{settings.tenent_base_url}/api/v1/tenants/{tenant_id}"
        try:
            async with httpx.AsyncClient(timeout=settings.tenent_timeout) as client:
                resp = await client.get(url)
        except httpx.TransportError as exc:
            raise TenantServiceUnavailableError(tenant_id) from exc

        if resp.status_code == 404:
            raise TenantNotFoundError(tenant_id)
        if resp.status_code != 200:
            raise TenantServiceUnavailableError(tenant_id)
