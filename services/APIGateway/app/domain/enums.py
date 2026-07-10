"""Domain enumerations for the API Gateway."""

from __future__ import annotations

from enum import StrEnum


class UpstreamService(StrEnum):
    """Registered upstream microservices the gateway can proxy to."""

    TENENT = "tenent"
    TENANT_PROVISIONING = "tenant_provisioning"
    OBSERVABILITY_MANAGEMENT = "observability_management"
    ORGANIZATION_MANAGEMENT = "organization_management"
    IAM = "iam"
    # UserManagement + UserLifecycleManagement + UserProfileManagement were
    # merged into one service ("User") — see services/User/TODO.md. One
    # upstream now covers /api/v1/users, /api/v1/platform-invitations, and
    # /api/v1/profiles.
    USER = "user"
    AUTHENTICATION = "authentication"


class CacheResult(StrEnum):
    HIT = "hit"
    MISS = "miss"
    SKIP = "skip"  # non-cacheable method or path
    ERROR = "error"  # Redis unavailable
