"""HTTP client to UserManagement — the underlying user record this service
orchestrates transitions for lives there, not here.

Two distinct call shapes, matching two existing patterns in this repo:

- Fail-fast (`get_user`/`restore_user`), shaped like
  `OrganizationManagement/app/infrastructure/clients/tenent_client.py`:
  the caller needs to know whether the call actually succeeded before
  reporting success itself.
- Fire-and-log (`sync_status`), shaped like
  `Tenent/app/infrastructure/clients/tenant_provisioning.py`: called after
  this service has already decided a transition is valid, to keep
  UserManagement's own status column in sync. Never raises — matches
  TenantLifecycle's documented contract with TenantManagement exactly
  ("fire-and-log — TM failures are non-fatal"). Same accepted tradeoff:
  if this call fails, this service's own record of the transition is
  still correct, but UserManagement's status can drift until retried.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx

from app.core.config import settings
from app.domain.enums import LifecycleStatus
from app.domain.exceptions import (
    RemoteUserNotDeletedError,
    RemoteUserNotFoundError,
    UserManagementUnavailableError,
)

logger = logging.getLogger(__name__)

_SYNC_ENDPOINT: dict[LifecycleStatus, str] = {
    LifecycleStatus.ACTIVE: "activate",
    LifecycleStatus.SUSPENDED: "suspend",
    # locked proxies to suspended on UserManagement's side — same pattern
    # as Tenant's locked-proxies-to-TM-as-suspended.
    LifecycleStatus.LOCKED: "suspend",
    LifecycleStatus.DEACTIVATED: "deactivate",
}


@dataclass
class RemoteUser:
    id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    status: str
    deleted_at: datetime | None


def _parse_user(body: dict[str, object]) -> RemoteUser:
    return RemoteUser(
        id=UUID(str(body["id"])),
        tenant_id=UUID(str(body["tenant_id"])),
        email=str(body["email"]),
        display_name=str(body["display_name"]),
        status=str(body["status"]),
        deleted_at=(
            datetime.fromisoformat(str(body["deleted_at"]))
            if body.get("deleted_at")
            else None
        ),
    )


class UserLifecycleClient:
    async def get_user(self, user_id: UUID, tenant_id: UUID) -> RemoteUser:
        url = f"{settings.user_management_base_url}/api/v1/users/{user_id}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.user_management_timeout
            ) as client:
                resp = await client.get(url, headers={"X-Tenant-ID": str(tenant_id)})
        except httpx.TransportError as exc:
            raise UserManagementUnavailableError(user_id) from exc

        if resp.status_code == 404:
            raise RemoteUserNotFoundError(user_id)
        if resp.status_code != 200:
            raise UserManagementUnavailableError(user_id)
        return _parse_user(resp.json())

    async def restore_user(self, user_id: UUID, tenant_id: UUID) -> RemoteUser:
        url = f"{settings.user_management_base_url}/api/v1/users/{user_id}/restore"
        try:
            async with httpx.AsyncClient(
                timeout=settings.user_management_timeout
            ) as client:
                resp = await client.post(url, headers={"X-Tenant-ID": str(tenant_id)})
        except httpx.TransportError as exc:
            raise UserManagementUnavailableError(user_id) from exc

        if resp.status_code == 404:
            raise RemoteUserNotFoundError(user_id)
        if resp.status_code == 409:
            raise RemoteUserNotDeletedError(user_id)
        if resp.status_code != 200:
            raise UserManagementUnavailableError(user_id)
        return _parse_user(resp.json())

    async def sync_status(
        self, user_id: UUID, tenant_id: UUID, to_status: LifecycleStatus
    ) -> None:
        """Never raises — a failed sync is logged, not propagated."""
        action = _SYNC_ENDPOINT.get(to_status)
        if action is None:
            return

        url = f"{settings.user_management_base_url}/api/v1/users/{user_id}/{action}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.user_management_timeout
            ) as client:
                resp = await client.post(
                    url, json={}, headers={"X-Tenant-ID": str(tenant_id)}
                )
                if resp.status_code == 200:
                    logger.info(
                        "user_management_sync_ok",
                        extra={"user_id": str(user_id), "action": action},
                    )
                else:
                    logger.warning(
                        "user_management_sync_unexpected_status",
                        extra={
                            "user_id": str(user_id),
                            "action": action,
                            "status": resp.status_code,
                            "body": resp.text[:200],
                        },
                    )
        except Exception as exc:
            logger.warning(
                "user_management_sync_error",
                extra={"user_id": str(user_id), "action": action, "error": str(exc)},
            )
