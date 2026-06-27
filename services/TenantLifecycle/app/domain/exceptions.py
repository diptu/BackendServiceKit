"""Domain exceptions for the Tenant Lifecycle Service."""

from __future__ import annotations

from uuid import UUID

from app.domain.enums import TenantLifecycleStatus


class TenantLifecycleNotFoundError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"No lifecycle record for tenant {tenant_id}.")
        self.tenant_id = tenant_id


class InvalidLifecycleTransitionError(Exception):
    def __init__(
        self, from_status: TenantLifecycleStatus, to_status: TenantLifecycleStatus
    ) -> None:
        super().__init__(
            f"Invalid lifecycle transition: {from_status} → {to_status}."
        )
        self.from_status = from_status
        self.to_status = to_status


class TenantLifecycleAlreadyExistsError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Lifecycle record already exists for tenant {tenant_id}.")
        self.tenant_id = tenant_id
