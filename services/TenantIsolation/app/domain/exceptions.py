"""Domain exceptions mapped to HTTP status codes in app/main.py."""

from __future__ import annotations

from uuid import UUID


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
