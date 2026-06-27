"""HTTP client for syncing lifecycle status to the TenantManagement service."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from app.core.config import settings
from app.domain.enums import TransitionType

logger = logging.getLogger(__name__)

# Maps each TenantLifecycle transition to the TenantManagement HTTP action.
# "lock" has no TM equivalent — we suspend at the TM level (closest concept).
_TM_ENDPOINT: dict[TransitionType, tuple[str, str]] = {
    TransitionType.ACTIVATE:   ("POST",   "/activate"),
    TransitionType.SUSPEND:    ("POST",   "/suspend"),
    TransitionType.REACTIVATE: ("POST",   "/activate"),
    TransitionType.LOCK:       ("POST",   "/suspend"),
    TransitionType.ARCHIVE:    ("POST",   "/archive"),
    TransitionType.DELETE:     ("DELETE", ""),
}


class TenantManagementClient:
    """Fire-and-log client: propagates lifecycle status changes to TenantManagement.

    Failures are logged as warnings and swallowed — TenantLifecycle remains the
    authoritative state machine and must not fail because TenantManagement is down.
    """

    def __init__(self) -> None:
        self._base = f"{settings.tenant_management_base_url.rstrip('/')}/api/v1/tenants"
        self._timeout = settings.tenant_management_timeout

    async def sync_transition(
        self,
        tenant_id: UUID,
        transition: TransitionType,
        *,
        reason: str | None = None,
    ) -> None:
        method, suffix = _TM_ENDPOINT[transition]
        url = f"{self._base}/{tenant_id}{suffix}"
        body = {"reason": reason} if reason else {}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(method, url, json=body)
                if resp.status_code not in (200, 204, 409):
                    logger.warning(
                        "TenantManagement status sync unexpected response",
                        extra={
                            "tenant_id": str(tenant_id),
                            "transition": transition,
                            "status_code": resp.status_code,
                            "body": resp.text[:200],
                        },
                    )
                elif resp.status_code == 409:
                    # TM already in target state or invalid source state — log, don't fail.
                    logger.info(
                        "TenantManagement status sync conflict (may already be in sync)",
                        extra={
                            "tenant_id": str(tenant_id),
                            "transition": transition,
                            "detail": resp.json().get("detail", ""),
                        },
                    )
                else:
                    logger.debug(
                        "TenantManagement status sync ok",
                        extra={"tenant_id": str(tenant_id), "transition": transition},
                    )
        except httpx.TransportError as exc:
            logger.warning(
                "TenantManagement status sync failed (network error)",
                extra={"tenant_id": str(tenant_id), "transition": transition, "error": str(exc)},
            )
        except Exception as exc:
            logger.warning(
                "TenantManagement status sync failed (unexpected error)",
                extra={"tenant_id": str(tenant_id), "transition": transition, "error": str(exc)},
            )
