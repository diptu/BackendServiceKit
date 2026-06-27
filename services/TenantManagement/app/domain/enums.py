"""Domain enumerations for the Tenant Management Service."""

from __future__ import annotations

from enum import StrEnum


class TenantStatus(StrEnum):
    """Lifecycle states of a Tenant entity."""

    DRAFT = "draft"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"


class OwnerRole(StrEnum):
    """Roles a contact may hold on a tenant."""

    OWNER = "owner"
    ADMIN = "admin"


# Valid state transitions: from_state → {allowed to_states}
VALID_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.DRAFT: frozenset({TenantStatus.PROVISIONING}),
    TenantStatus.PROVISIONING: frozenset({TenantStatus.ACTIVE, TenantStatus.DRAFT}),
    TenantStatus.ACTIVE: frozenset({TenantStatus.SUSPENDED, TenantStatus.ARCHIVED}),
    TenantStatus.SUSPENDED: frozenset({TenantStatus.ACTIVE, TenantStatus.ARCHIVED}),
    TenantStatus.ARCHIVED: frozenset({TenantStatus.DELETED}),
    TenantStatus.DELETED: frozenset(),
}
