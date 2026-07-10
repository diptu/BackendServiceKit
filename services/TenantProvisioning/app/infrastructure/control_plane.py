"""Registers a newly-provisioned tenant database in the Tenent Control Plane.

The last workflow step: once the database exists and is migrated, the tenant →
database mapping (and its subdomain) is written to Tenent so every service's
connection router and the gateway's subdomain resolver can find it. Injectable
so tests use a null/fake registrar with no network.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

import httpx

from app.infrastructure.provisioner import ProvisionedDatabase


class ControlPlaneRegistrar(ABC):
    @abstractmethod
    async def register(
        self,
        *,
        tenant_id: uuid.UUID,
        subdomain: str,
        db: ProvisionedDatabase,
        region: str | None,
    ) -> None: ...

    @abstractmethod
    async def deprovision(self, tenant_id: uuid.UUID) -> None: ...


class NullControlPlaneRegistrar(ControlPlaneRegistrar):
    """No-op registrar for dev/test or when registration is disabled."""

    async def register(
        self,
        *,
        tenant_id: uuid.UUID,
        subdomain: str,
        db: ProvisionedDatabase,
        region: str | None,
    ) -> None:
        return None

    async def deprovision(self, tenant_id: uuid.UUID) -> None:
        return None


class HttpxControlPlaneRegistrar(ControlPlaneRegistrar):
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def register(
        self,
        *,
        tenant_id: uuid.UUID,
        subdomain: str,
        db: ProvisionedDatabase,
        region: str | None,
    ) -> None:
        payload = {
            "subdomain": subdomain,
            "db_driver": db.driver,
            "db_host": db.host,
            "db_port": db.port,
            "db_name": db.name,
            "db_user": db.user,
            "secret_ref": db.secret_ref,
            "region": region,
            "status": "active",
        }
        url = f"{self._base_url}/api/v1/control-plane/connections/{tenant_id}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

    async def deprovision(self, tenant_id: uuid.UUID) -> None:
        url = f"{self._base_url}/api/v1/control-plane/connections/{tenant_id}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.delete(url)
            if resp.status_code not in (204, 404):
                resp.raise_for_status()
