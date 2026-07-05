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
    USER_MANAGEMENT = "user_management"
    USER_LIFECYCLE_MANAGEMENT = "user_lifecycle_management"
    USER_PROFILE_MANAGEMENT = "user_profile_management"


class CacheResult(StrEnum):
    HIT = "hit"
    MISS = "miss"
    SKIP = "skip"   # non-cacheable method or path
    ERROR = "error"  # Redis unavailable
