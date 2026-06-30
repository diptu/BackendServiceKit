"""Domain enumerations for the API Gateway."""

from __future__ import annotations

from enum import StrEnum


class UpstreamService(StrEnum):
    """Registered upstream microservices the gateway can proxy to."""

    TENANT_MANAGEMENT = "tenant_management"
    TENANT_LIFECYCLE = "tenant_lifecycle"
    TENANT_PROVISIONING = "tenant_provisioning"


class CacheResult(StrEnum):
    HIT = "hit"
    MISS = "miss"
    SKIP = "skip"   # non-cacheable method or path
    ERROR = "error"  # Redis unavailable
