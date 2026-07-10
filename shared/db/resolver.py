"""Resolve a tenant_id to its database connection string.

`TenantConnectionResolver` is the seam between "which tenant" and "which
database." The concrete `TemplateConnectionResolver` is a deliberately simple
stand-in for the Tenent-owned **Control Plane**: it derives a per-tenant URL
from a template (plus explicit overrides) so Siloed multi-tenancy is usable
today, and can be swapped for a `ControlPlaneConnectionResolver` (an HTTP
client to Tenent) later without any caller change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol
from uuid import UUID

import httpx

_TENANT_PLACEHOLDER = "{tenant}"


class ControlPlaneUnavailableError(RuntimeError):
    """A tenant could not be resolved to a connection string. Callers must
    fail closed — never fall back to a shared database."""


class TenantConnectionResolver(ABC):
    @abstractmethod
    async def resolve(self, tenant_id: UUID) -> str:
        """Return the SQLAlchemy connection URL for `tenant_id`, or raise
        ControlPlaneUnavailableError if it cannot be determined."""
        raise NotImplementedError


class TemplateConnectionResolver(TenantConnectionResolver):
    """Derives a connection string from a URL template containing a
    ``{tenant}`` placeholder, substituted with the tenant's 32-char hex id
    (a safe SQL identifier fragment). Explicit `overrides` (keyed by the
    string form of the tenant UUID) win over the template — for tenants whose
    database lives on a different host."""

    def __init__(self, template: str, overrides: dict[str, str] | None = None) -> None:
        self._overrides = dict(overrides or {})
        if _TENANT_PLACEHOLDER not in template and not self._overrides:
            raise ValueError(
                "TemplateConnectionResolver needs a '{tenant}' placeholder in "
                "the template or at least one explicit override."
            )
        self._template = template

    async def resolve(self, tenant_id: UUID) -> str:
        override = self._overrides.get(str(tenant_id))
        if override is not None:
            return override
        if _TENANT_PLACEHOLDER not in self._template:
            raise ControlPlaneUnavailableError(
                f"No connection mapping for tenant {tenant_id}."
            )
        return self._template.replace(_TENANT_PLACEHOLDER, tenant_id.hex)


class _AsyncGetClient(Protocol):
    async def get(self, url: str) -> httpx.Response: ...


class ControlPlaneConnectionResolver(TenantConnectionResolver):
    """Resolves a tenant's connection string from the **Tenent Control Plane**
    (`GET /api/v1/control-plane/connections/{tenant_id}/dsn`).

    This is the production replacement for `TemplateConnectionResolver`: the
    tenant→database mapping and credentials live in Tenent, not in each
    consuming service's config. A caller swaps one for the other without any
    other change. An injectable `http_client` lets tests point it straight at
    Tenent's ASGI app with no network.
    """

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

    async def resolve(self, tenant_id: UUID) -> str:
        path = f"/api/v1/control-plane/connections/{tenant_id}/dsn"
        try:
            if self._client is not None:
                response = await self._client.get(path)
            else:
                async with httpx.AsyncClient(
                    base_url=self._base_url, timeout=self._timeout
                ) as client:
                    response = await client.get(path)
        except httpx.HTTPError as exc:
            raise ControlPlaneUnavailableError(
                f"Control Plane unreachable for tenant {tenant_id}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise ControlPlaneUnavailableError(
                f"Control Plane returned {response.status_code} for tenant {tenant_id}."
            )
        dsn = response.json().get("dsn")
        if not dsn:
            raise ControlPlaneUnavailableError(
                f"Control Plane returned no dsn for tenant {tenant_id}."
            )
        return str(dsn)
