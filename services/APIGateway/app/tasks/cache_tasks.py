"""Cache management tasks — warming and bulk invalidation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="api_gateway.warm_tenant_cache",
    max_retries=2,
    default_retry_delay=60,
)
def warm_tenant_cache(self: Any, tenant_id: str) -> None:
    """Pre-warm cache entries for a frequently accessed tenant.

    Calls TenantManagement and TenantLifecycle GET endpoints synchronously
    (inside the Celery worker) so subsequent API Gateway requests hit the cache.
    """
    import httpx

    from app.core.config import settings

    urls = [
        f"{settings.tenant_management_base_url}/api/v1/tenants/{tenant_id}",
        f"{settings.tenant_lifecycle_base_url}/api/v1/tenant-lifecycle/{tenant_id}/history",
    ]
    try:
        with httpx.Client(timeout=10.0) as client:
            for url in urls:
                try:
                    client.get(url)
                    logger.info("cache_warm_fetch", extra={"url": url, "tenant_id": tenant_id})
                except Exception as exc:
                    logger.warning(
                        "cache_warm_fetch_failed",
                        extra={"url": url, "tenant_id": tenant_id, "error": str(exc)},
                    )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(
    bind=True,
    name="api_gateway.bulk_invalidate_tenant",
    max_retries=3,
    default_retry_delay=10,
)
def bulk_invalidate_tenant(self: Any, tenant_id: str) -> dict[str, int]:
    """Invalidate all cache entries for a tenant across all registered upstreams.

    Returns a dict mapping upstream → keys_deleted.
    """
    from app.domain.enums import UpstreamService
    from app.infrastructure.cache.redis_client import create_redis_client
    from app.services.cache_service import CacheService

    results: dict[str, int] = {}
    try:
        redis = asyncio.run(create_redis_client())
        cache = CacheService(redis)
        for upstream in UpstreamService:
            deleted = asyncio.run(cache.invalidate_tenant(tenant_id, upstream.value))
            results[upstream.value] = deleted
        asyncio.run(redis.aclose())
        logger.info(
            "bulk_invalidation_complete",
            extra={"tenant_id": tenant_id, "results": results},
        )
        return results
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
