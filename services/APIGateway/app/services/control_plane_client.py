"""Client for the Tenent Control Plane's subdomain → tenant resolution.

The gateway's Tenant Resolver calls this to turn a request's subdomain into a
tenant id (`GET /api/v1/control-plane/resolve?subdomain=<sub>`). It only ever
receives the tenant id and status — never connection coordinates or
credentials, which the Control Plane deliberately withholds from this route.

`http_client` is injectable so the resolver can share the gateway's pooled
`httpx.AsyncClient` in production and tests can supply a fake with no network.
"""

from __future__ import annotations

import uuid
from typing import Protocol

import httpx


class ControlPlaneUnavailableError(RuntimeError):
    """The Control Plane could not be reached or returned an unexpected error.
    The caller must fail closed rather than route with an unresolved tenant."""


class ResolvedTenant:
    __slots__ = ("tenant_id", "status")

    def __init__(self, tenant_id: uuid.UUID, status: str) -> None:
        self.tenant_id = tenant_id
        self.status = status


class _AsyncGetClient(Protocol):
    async def get(self, url: str) -> httpx.Response: ...


class ControlPlaneClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        http_client: _AsyncGetClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = http_client

    async def resolve_subdomain(self, subdomain: str) -> ResolvedTenant | None:
        """Return the tenant a subdomain maps to, `None` if no tenant is
        registered for it (404), or raise ControlPlaneUnavailableError on any
        transport/5xx failure."""
        url = f"{self._base_url}/api/v1/control-plane/resolve?subdomain={subdomain}"
        try:
            if self._client is not None:
                response = await self._client.get(url)
            else:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url)
        except httpx.HTTPError as exc:
            raise ControlPlaneUnavailableError(str(exc)) from exc

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ControlPlaneUnavailableError(f"Control Plane returned {response.status_code}.")
        payload = response.json()
        try:
            return ResolvedTenant(
                tenant_id=uuid.UUID(str(payload["tenant_id"])),
                status=str(payload["status"]),
            )
        except (KeyError, ValueError) as exc:
            raise ControlPlaneUnavailableError(
                "Control Plane returned a malformed resolve response."
            ) from exc
