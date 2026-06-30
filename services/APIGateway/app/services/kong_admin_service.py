"""KongAdminService — async client for the Kong Admin API (DB-less compatible)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Maps FastAPI route prefixes to the Kong service they belong to.
KONG_ROUTE_PREFIX_MAP: dict[str, str] = {
    "/api/v1/tenants": "nutratenant-tenent",
    "/api/v1/lifecycle": "nutratenant-tenent",
    "/api/v1/isolation": "nutratenant-tenent",
    "/api/v1/provisioning": "nutratenant-tenant-provisioning",
    "/api/v1/gateway": "nutratenant-api-gateway",
}


@dataclass
class KongSyncResult:
    synced: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.synced) + len(self.skipped) + len(self.failed)


class KongAdminService:
    """Thin async client wrapping the Kong Admin API.

    Accepts an optional pre-existing httpx.AsyncClient (e.g., the app-level
    connection pool). Always uses absolute URLs so callers can pass any client
    regardless of whether it has a base_url configured.
    """

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._base_url = settings.kong_admin_url.rstrip("/")
        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                headers={"Content-Type": "application/json"},
            )
            self._owns_client = True

    async def get_status(self) -> dict[str, Any]:
        """Return Kong node status (connections, memory, worker states)."""
        resp = await self._client.get(f"{self._base_url}/status")
        resp.raise_for_status()
        return resp.json()

    async def list_services(self) -> list[dict[str, Any]]:
        """Return all services registered with Kong."""
        resp = await self._client.get(f"{self._base_url}/services")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def list_routes(self) -> list[dict[str, Any]]:
        """Return all routes registered with Kong."""
        resp = await self._client.get(f"{self._base_url}/routes")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def list_plugins(self) -> list[dict[str, Any]]:
        """Return all active plugins (global + service-scoped + route-scoped)."""
        resp = await self._client.get(f"{self._base_url}/plugins")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def sync_routes(self) -> KongSyncResult:
        """Upsert FastAPI route registry into Kong via the Admin API.

        For each route in RouteService, creates or updates the corresponding
        Kong service + route. Idempotent — safe to call multiple times.
        Useful for dynamically registering routes without reloading kong.yml.
        """
        from app.services.route_service import RouteService

        result = KongSyncResult()
        route_svc = RouteService()

        for route in route_svc.routes:
            service_name = f"nutratenant-{route.upstream.value.replace('_', '-')}"
            route_slug = route.prefix.lstrip("/").replace("/", "-")
            route_name = f"{service_name}-{route_slug}"

            # Upsert the upstream service (idempotent PUT)
            try:
                svc_resp = await self._client.put(
                    f"{self._base_url}/services/{service_name}",
                    json={"name": service_name, "url": route.base_url},
                )
                svc_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "kong_service_upsert_failed",
                    extra={"service": service_name, "status": exc.response.status_code},
                )
                result.failed.append(route.prefix)
                continue
            except httpx.TransportError as exc:
                logger.warning("kong_admin_unreachable", extra={"error": str(exc)})
                result.failed.append(route.prefix)
                continue

            # Upsert the route (idempotent PUT)
            try:
                rt_resp = await self._client.put(
                    f"{self._base_url}/services/{service_name}/routes/{route_name}",
                    json={
                        "name": route_name,
                        "paths": [route.prefix],
                        "strip_path": False,
                        "preserve_host": False,
                        "protocols": ["http", "https"],
                    },
                )
                rt_resp.raise_for_status()
                result.synced.append(route.prefix)
                logger.info(
                    "kong_route_synced",
                    extra={"prefix": route.prefix, "service": service_name},
                )
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "kong_route_upsert_failed",
                    extra={"route": route_name, "status": exc.response.status_code},
                )
                result.failed.append(route.prefix)

        return result

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
