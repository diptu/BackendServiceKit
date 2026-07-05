"""HTTP client to UserManagement — validates a user_id exists before this
service creates its first row for it.

Fail-fast, shaped like
`OrganizationManagement/app/infrastructure/clients/tenent_client.py`'s
`assert_tenant_exists` and
`UserLifecycleManagement/app/infrastructure/clients/user_lifecycle_client.py`'s
`get_user`: a profile/preferences/contact/avatar row for a user_id
UserManagement doesn't have is a real correctness error the caller needs
to see, not something to silently accept. Called only once per user_id —
on the first write, not on every read (see ProfileService/AvatarService).
"""

from __future__ import annotations

from uuid import UUID

import httpx

from app.core.config import settings
from app.domain.exceptions import (
    RemoteUserNotFoundError,
    UserManagementUnavailableError,
)


class UserProfileClient:
    async def assert_user_exists(self, user_id: UUID, tenant_id: UUID) -> None:
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
