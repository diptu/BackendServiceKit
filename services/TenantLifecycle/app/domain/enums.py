"""Domain enumerations for the Tenant Lifecycle Service."""

from __future__ import annotations

from enum import StrEnum


class TenantLifecycleStatus(StrEnum):
    """All possible lifecycle states of a tenant.

    State descriptions:
      PROVISIONING  Async infrastructure setup is in progress (DB sharding, API keys, VPC).
                    Entry point for TL. TM mirrors this state.
      PENDING       Provisioning complete; awaiting final confirmation or compliance sign-off.
                    TM mirrors this state. No user access yet.
      ACTIVE        Fully operational. Tenants are billed and users can log in.
      SUSPENDED     Service paused — non-payment or policy violation. Data is retained.
                    All logins and API access are blocked. TM mirrors as "suspended".
      LOCKED        Preventative hold for security incidents (e.g. unusual API traffic).
                    Admin-triggered; blocks writes while investigation proceeds.
                    TM proxies this as "suspended" (TM has no locked state).
      ARCHIVED      Long-term cold storage after contract end. No production access.
                    Data retained for compliance/audit. Prerequisite for deletion.
      DELETED       Permanent soft-delete. Hard purge (GDPR) is handled by the
                    Offboarding Service after the retention period expires.
    """

    PROVISIONING = "provisioning"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    ARCHIVED = "archived"
    DELETED = "deleted"


class TransitionType(StrEnum):
    """Named action types that drive lifecycle transitions."""

    PROVISION = "provision"
    PEND = "pend"
    ACTIVATE = "activate"
    SUSPEND = "suspend"
    REACTIVATE = "reactivate"
    LOCK = "lock"
    UNLOCK = "unlock"
    ARCHIVE = "archive"
    DELETE = "delete"


# Valid state transitions per README.md state machine diagram.
# Key constraints:
#   - provisioning → pending is mandatory before activation (no shortcut to active)
#   - deleted is only reachable via archived (no direct deletion from operational states)
#   - suspended → provisioning is explicitly NOT allowed (once operational, always forward)
VALID_TRANSITIONS: dict[TenantLifecycleStatus, frozenset[TenantLifecycleStatus]] = {
    TenantLifecycleStatus.PROVISIONING: frozenset({TenantLifecycleStatus.PENDING}),
    TenantLifecycleStatus.PENDING: frozenset({TenantLifecycleStatus.ACTIVE}),
    TenantLifecycleStatus.ACTIVE: frozenset(
        {
            TenantLifecycleStatus.SUSPENDED,
            TenantLifecycleStatus.LOCKED,
            TenantLifecycleStatus.ARCHIVED,
        }
    ),
    TenantLifecycleStatus.SUSPENDED: frozenset(
        {TenantLifecycleStatus.ACTIVE, TenantLifecycleStatus.ARCHIVED}
    ),
    # LOCKED → ACTIVE: security incident resolved; tenant resumes normal operation.
    # LOCKED → ARCHIVED: incident deemed terminal (fraud, breach); tenant decommissioned.
    TenantLifecycleStatus.LOCKED: frozenset(
        {TenantLifecycleStatus.ACTIVE, TenantLifecycleStatus.ARCHIVED}
    ),
    TenantLifecycleStatus.ARCHIVED: frozenset({TenantLifecycleStatus.DELETED}),
    TenantLifecycleStatus.DELETED: frozenset(),
}
