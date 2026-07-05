"""Domain exceptions."""

from __future__ import annotations

from uuid import UUID


class OrganizationNotFoundError(Exception):
    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"Organization {organization_id} not found.")
        self.organization_id = organization_id


class OrganizationSlugConflictError(Exception):
    """Raised when a slug is already taken within the same tenant."""

    def __init__(self, tenant_id: UUID, slug: str) -> None:
        super().__init__(
            f"Organization slug '{slug}' is already taken in tenant {tenant_id}."
        )
        self.tenant_id = tenant_id
        self.slug = slug


class OrganizationDeletedError(Exception):
    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"Organization {organization_id} has been deleted.")
        self.organization_id = organization_id


class InvalidOrganizationTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            f"Invalid organization state transition: {from_status} → {to_status}."
        )
        self.from_status = from_status
        self.to_status = to_status


class TenantNotFoundError(Exception):
    """Raised when the tenant_id an organization is created under doesn't exist."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant {tenant_id} not found.")
        self.tenant_id = tenant_id


class TenantServiceUnavailableError(Exception):
    """Raised when Tenent can't be reached to validate a tenant_id."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Could not verify tenant {tenant_id}: Tenent is unreachable.")
        self.tenant_id = tenant_id
