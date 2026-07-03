"""Domain enumerations for the API Gateway."""

from __future__ import annotations

from enum import StrEnum


class UpstreamService(StrEnum):
    """Registered upstream microservices the gateway can proxy to."""

    TENENT = "tenent"
    TENANT_PROVISIONING = "tenant_provisioning"
    LOGGING = "logging"
    DISTRIBUTED_TRACING = "distributed_tracing"
    METRICS_COLLECTION = "metrics_collection"


class CacheResult(StrEnum):
    HIT = "hit"
    MISS = "miss"
    SKIP = "skip"   # non-cacheable method or path
    ERROR = "error"  # Redis unavailable
