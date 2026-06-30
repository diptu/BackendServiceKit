"""Domain exceptions — merged from TenantManagement, TenantLifecycle, TenantIsolation."""

from __future__ import annotations

from uuid import UUID

from app.domain.enums import TenantLifecycleStatus, TenantStatus


# ---------------------------------------------------------------------------
# TenantManagement exceptions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TenantLifecycle exceptions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TenantIsolation exceptions
# ---------------------------------------------------------------------------


class IsolationError(Exception):
    """Base for all isolation domain errors."""


class IsolationViolationError(IsolationError):
    """403 — cross-tenant access attempt blocked."""

    def __init__(self, detail: str = "Cross-tenant access denied.") -> None:
        super().__init__(detail)


class PolicyNotFoundError(IsolationError):
    """404 — no isolation policy found."""

    def __init__(self, policy_id: UUID) -> None:
        super().__init__(f"Isolation policy {policy_id} not found.")
        self.policy_id = policy_id


class ResourceClaimNotFoundError(IsolationError):
    """404 — resource has no registered claim."""

    def __init__(self, resource_id: str, resource_type: str) -> None:
        super().__init__(
            f"No claim found for resource '{resource_id}' of type '{resource_type}'."
        )
        self.resource_id = resource_id
        self.resource_type = resource_type


class ResourceClaimConflictError(IsolationError):
    """409 — resource already claimed by a different tenant."""

    def __init__(self, resource_id: str, resource_type: str, owner_tenant_id: UUID) -> None:
        super().__init__(
            f"Resource '{resource_id}' (type='{resource_type}') is already claimed "
            f"by tenant {owner_tenant_id}."
        )
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.owner_tenant_id = owner_tenant_id


class InvalidQueryFilterError(IsolationError):
    """422 — query filter is missing required tenant_id scoping."""

    def __init__(self, detail: str = "Query filter missing tenant_id.") -> None:
        super().__init__(detail)


class ContextResolutionError(IsolationError):
    """401 — cannot extract tenant context from the provided token."""

    def __init__(self, detail: str = "Cannot resolve tenant context from token.") -> None:
        super().__init__(detail)


class IsolationValidationError(IsolationError):
    """422 — domain-level input validation failure."""
