"""HTTP client for triggering TenantProvisioning when a tenant enters provisioning state."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TenantProvisioningClient:
    async def start_provisioning(self, tenant_id: UUID) -> None:
        """Notify TenantProvisioning to start the provisioning workflow.

        Never raises — TP failures are non-fatal to the lifecycle transition.
        """
        url = f"{settings.tenant_provisioning_base_url}/api/v1/provisioning/tenants"
        try:
            async with httpx.AsyncClient(
                timeout=settings.tenant_provisioning_timeout
            ) as client:
                resp = await client.post(url, json={"tenant_id": str(tenant_id)})
                if resp.status_code in (200, 201, 409):
                    logger.info(
                        "tp_provisioning_triggered",
                        extra={"tenant_id": str(tenant_id), "status": resp.status_code},
                    )
                else:
                    logger.warning(
                        "tp_provisioning_unexpected_status",
                        extra={
                            "tenant_id": str(tenant_id),
                            "status": resp.status_code,
                            "body": resp.text[:200],
                        },
                    )
        except httpx.TransportError as exc:
            logger.warning(
                "tp_provisioning_transport_error",
                extra={"tenant_id": str(tenant_id), "error": str(exc)},
            )
        except Exception as exc:
            logger.warning(
                "tp_provisioning_error",
                extra={"tenant_id": str(tenant_id), "error": str(exc)},
            )
