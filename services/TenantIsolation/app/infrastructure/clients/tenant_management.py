"""Fire-and-log HTTP client for TenantManagement service."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TenantManagementClient:
    async def is_tenant_active(self, tenant_id: UUID) -> bool:
        """Return True if active, False if inactive/unknown. Never raises."""
        try:
            url = f"{settings.tenant_management_base_url}/api/v1/tenants/{tenant_id}"
            async with httpx.AsyncClient(timeout=settings.tenant_management_timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return str(data.get("status", "")) == "active"
                return False
        except Exception as exc:
            logger.warning(
                "tenant_management_check_failed",
                extra={"tenant_id": str(tenant_id), "error": str(exc)},
            )
            return True
