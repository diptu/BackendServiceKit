"""Domain enumerations for the Tenant Management Service."""

from __future__ import annotations

from enum import StrEnum


class TenantStatus(StrEnum):
    """Lifecycle states of a Tenant entity.

    State descriptions:
      DRAFT         Initial record created; no resources allocated yet.
      PROVISIONING  Async infrastructure setup in progress (DB, API keys, VPC).
                    Transitions to ACTIVE once provisioning succeeds.
      ACTIVE        Fully operational and billed.
      SUSPENDED     Service paused — non-payment or policy violation; data retained.
      ARCHIVED      Cold storage after contract end; data kept for audit compliance.
      DELETED       Permanent soft-delete; hard purge by Offboarding Service.
    """

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


# Valid state transitions per TenentStates.md (TR-001, TR-004).
# Admin override allows any → deleted; recovery path: suspended → active.
VALID_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.DRAFT: frozenset({TenantStatus.PROVISIONING, TenantStatus.DELETED}),
    TenantStatus.PROVISIONING: frozenset({TenantStatus.ACTIVE, TenantStatus.DELETED}),
    TenantStatus.ACTIVE: frozenset(
        {TenantStatus.SUSPENDED, TenantStatus.ARCHIVED, TenantStatus.DELETED}
    ),
    TenantStatus.SUSPENDED: frozenset(
        {TenantStatus.ACTIVE, TenantStatus.ARCHIVED, TenantStatus.DELETED}
    ),
    TenantStatus.ARCHIVED: frozenset({TenantStatus.DELETED}),
    TenantStatus.DELETED: frozenset(),
}
