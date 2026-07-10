"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class ProvisioningJobNotFoundError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"No provisioning job for tenant {tenant_id}.")
        self.tenant_id = tenant_id


class ProvisioningInProgressError(Exception):
    """A provisioning run for this tenant is already in progress."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Provisioning for tenant {tenant_id} is already running.")
        self.tenant_id = tenant_id
