"""Domain enumerations for the Tenant Management Service."""

from __future__ import annotations

from enum import StrEnum


class TenantStatus(StrEnum):
    """Lifecycle states of a Tenant entity.

    State descriptions:
      DRAFT         Initial record created; no resources allocated yet.
      PROVISIONING  Async infrastructure setup in progress (DB, API keys, VPC).
      PENDING       Provisioning complete; awaiting compliance/confirmation gate.
                    No user access until explicitly activated.
      ACTIVE        Fully operational and billed.
      SUSPENDED     Service paused — non-payment or policy violation; data retained.
      ARCHIVED      Cold storage after contract end; data kept for audit compliance.
      DELETED       Permanent soft-delete; hard purge by Offboarding Service.
    """

    DRAFT = "draft"
    PROVISIONING = "provisioning"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"


class OwnerRole(StrEnum):
    """Roles a contact may hold on a tenant."""

    OWNER = "owner"
    ADMIN = "admin"


# Valid state transitions per CLAUDE.md state machine (TM view).
# Key constraint: provisioning → pending is mandatory before activation.
# Note: DELETED is enforced separately in TenantService.delete() (ARCHIVED-only gate).
VALID_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.DRAFT: frozenset({TenantStatus.PROVISIONING}),
    TenantStatus.PROVISIONING: frozenset({TenantStatus.PENDING}),
    TenantStatus.PENDING: frozenset({TenantStatus.ACTIVE}),
    TenantStatus.ACTIVE: frozenset({TenantStatus.SUSPENDED, TenantStatus.ARCHIVED}),
    TenantStatus.SUSPENDED: frozenset({TenantStatus.ACTIVE, TenantStatus.ARCHIVED}),
    TenantStatus.ARCHIVED: frozenset({TenantStatus.DELETED}),
    TenantStatus.DELETED: frozenset(),
}
