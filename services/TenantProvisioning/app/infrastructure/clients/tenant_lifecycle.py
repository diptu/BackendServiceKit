"""HTTP client for calling TenantLifecycle's pending transition.

Fire-and-log pattern: failures are logged as warnings but never re-raised.
TenantLifecycle is authoritative; TP's job completion is not gated on TL's availability.
"""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TenantLifecycleClient:

    async def advance_to_pending(
        self, tenant_id: UUID, *, reason: str | None = None
    ) -> None:
        """Call TL's PUT /pending to advance a tenant from provisioning → pending.

        Never raises — TL failures are non-fatal to provisioning completion.
        """
        url = (
            f"{settings.tenant_lifecycle_base_url}"
            f"/api/v1/tenant-lifecycle/{tenant_id}/pending"
        )
        body: dict[str, str | None] = {"reason": reason}
        try:
            async with httpx.AsyncClient(
                timeout=settings.tenant_lifecycle_timeout
            ) as client:
                resp = await client.put(url, json=body)
                if resp.status_code in (200, 204, 409):
                    logger.info(
                        "tl_pending_synced",
                        extra={"tenant_id": str(tenant_id), "status": resp.status_code},
                    )
                else:
                    logger.warning(
                        "tl_pending_unexpected_status",
                        extra={
                            "tenant_id": str(tenant_id),
                            "status": resp.status_code,
                            "body": resp.text[:200],
                        },
                    )
        except httpx.TransportError as exc:
            logger.warning(
                "tl_pending_transport_error",
                extra={"tenant_id": str(tenant_id), "error": str(exc)},
            )
        except Exception as exc:
            logger.warning(
                "tl_pending_error",
                extra={"tenant_id": str(tenant_id), "error": str(exc)},
            )
