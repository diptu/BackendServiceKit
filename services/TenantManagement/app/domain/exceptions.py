"""Domain exceptions for the Tenant Management Service."""

from __future__ import annotations

from uuid import UUID

from app.domain.enums import TenantStatus


class TenantNotFoundError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant {tenant_id} not found.")
        self.tenant_id = tenant_id


class TenantNameConflictError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Tenant name '{name}' is already taken.")
        self.name = name


class TenantSlugConflictError(Exception):
    def __init__(self, slug: str) -> None:
        super().__init__(f"Tenant slug '{slug}' is already taken.")
        self.slug = slug


class InvalidTenantTransitionError(Exception):
    def __init__(self, from_status: TenantStatus, to_status: TenantStatus) -> None:
        super().__init__(
            f"Invalid tenant state transition: {from_status} → {to_status}."
        )
        self.from_status = from_status
        self.to_status = to_status


class TenantLockedError(Exception):
    """Raised when a write is attempted on an archived tenant."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant {tenant_id} is archived and read-only.")
        self.tenant_id = tenant_id


class TenantDeletedError(Exception):
    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant {tenant_id} has been deleted.")
        self.tenant_id = tenant_id


class TenantOwnerRequiredError(Exception):
    """Raised when removing the last owner of a tenant."""

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant {tenant_id} must have at least one active owner.")
        self.tenant_id = tenant_id


class TenantContactConflictError(Exception):
    """Raised when a user is already an active contact on the tenant."""

    def __init__(self, tenant_id: UUID, user_id: UUID) -> None:
        super().__init__(
            f"User {user_id} is already an active owner/admin of tenant {tenant_id}."
        )
        self.tenant_id = tenant_id
        self.user_id = user_id


class TenantContactNotFoundError(Exception):
    """Raised when a contact record cannot be found."""

    def __init__(self, contact_id: UUID) -> None:
        super().__init__(f"Contact {contact_id} not found.")
        self.contact_id = contact_id
