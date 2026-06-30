"""Domain enumerations — merged from TenantManagement, TenantLifecycle, TenantIsolation."""

from __future__ import annotations

from enum import StrEnum


# ---------------------------------------------------------------------------
# TenantManagement enums
# ---------------------------------------------------------------------------


class TenantStatus(StrEnum):
    DRAFT = "draft"
    PROVISIONING = "provisioning"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    DELETED = "deleted"


class OwnerRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"


VALID_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.DRAFT: frozenset({TenantStatus.PROVISIONING}),
    TenantStatus.PROVISIONING: frozenset({TenantStatus.PENDING}),
    TenantStatus.PENDING: frozenset({TenantStatus.ACTIVE}),
    TenantStatus.ACTIVE: frozenset({TenantStatus.SUSPENDED, TenantStatus.ARCHIVED}),
    TenantStatus.SUSPENDED: frozenset({TenantStatus.ACTIVE, TenantStatus.ARCHIVED}),
    TenantStatus.ARCHIVED: frozenset({TenantStatus.DELETED}),
    TenantStatus.DELETED: frozenset(),
}


# ---------------------------------------------------------------------------
# TenantLifecycle enums
# ---------------------------------------------------------------------------


class TenantLifecycleStatus(StrEnum):
    PROVISIONING = "provisioning"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    ARCHIVED = "archived"
    DELETED = "deleted"


class TransitionType(StrEnum):
    PROVISION = "provision"
    PEND = "pend"
    ACTIVATE = "activate"
    SUSPEND = "suspend"
    REACTIVATE = "reactivate"
    LOCK = "lock"
    UNLOCK = "unlock"
    ARCHIVE = "archive"
    DELETE = "delete"


LIFECYCLE_VALID_TRANSITIONS: dict[
    TenantLifecycleStatus, frozenset[TenantLifecycleStatus]
] = {
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
        {
            TenantLifecycleStatus.ACTIVE,
            TenantLifecycleStatus.ARCHIVED,
        }
    ),
    TenantLifecycleStatus.LOCKED: frozenset(
        {
            TenantLifecycleStatus.ACTIVE,
            TenantLifecycleStatus.ARCHIVED,
        }
    ),
    TenantLifecycleStatus.ARCHIVED: frozenset({TenantLifecycleStatus.DELETED}),
    TenantLifecycleStatus.DELETED: frozenset(),
}


# ---------------------------------------------------------------------------
# TenantIsolation enums
# ---------------------------------------------------------------------------


class PolicyType(StrEnum):
    STRICT = "strict"
    PARTNER = "partner"
    INTERNAL = "internal"


class IsolationDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class ResourceType(StrEnum):
    DOCUMENT = "document"
    WORKSPACE = "workspace"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    GROUP = "group"
    ORGANIZATION = "organization"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    BILLING_RECORD = "billing_record"
    AUDIT_LOG = "audit_log"


class AccessAction(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
