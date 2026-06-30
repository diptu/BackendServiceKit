"""FastAPI application factory for the API Gateway."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aio_pika
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.openapi import TAGS_METADATA
from app.infrastructure.cache.redis_client import close_redis_client, create_redis_client
from app.infrastructure.messaging.consumer import TenantEventConsumer

logger = logging.getLogger(__name__)

_DESCRIPTION = """\
## Overview

The **API Gateway** is the single entry point for all client traffic in the NutraTenant
platform. It provides:

- **Reverse proxy** — routes requests to TenantManagement and TenantLifecycle microservices
- **Redis caching** — caches GET responses with configurable TTL per upstream
- **Cache invalidation** — purges stale entries on writes and on RabbitMQ tenant-change events
- **Celery audit tasks** — ships request/response audit records asynchronously
- **RabbitMQ events** — publishes `gateway.request.completed` after every proxied request

---

## Route Map

| Path Prefix | Upstream Service | Cache TTL |
|---|---|---|
| `/api/v1/tenants/**` | TenantManagement (:8000) | 5 min |
| `/api/v1/tenant-lifecycle/**` | TenantLifecycle (:8001) | 60 s |

---

## Cache Headers

| Header | Value |
|---|---|
| `X-Cache` | `HIT` / `MISS` / `BYPASS` |
| `X-Request-ID` | Unique request trace ID |

Pass `X-Tenant-ID` on write requests to enable per-tenant cache invalidation.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(debug=settings.debug)
    logger.info(
        "gateway_starting",
        extra={
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
    )

    # ── Shared async HTTP client (connection-pooled) ───────────────────
    app.state.http_client = httpx.AsyncClient(
        timeout=settings.upstream_timeout,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
    )

    # ── Redis ─────────────────────────────────────────────────────────
    app.state.redis = None
    try:
        redis_client = await create_redis_client()
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("redis_connected", extra={"url": settings.redis_url})
    except Exception as exc:
        logger.warning(
            "redis_unavailable",
            extra={"url": settings.redis_url, "error": str(exc)},
        )

    # ── RabbitMQ ──────────────────────────────────────────────────────
    app.state.rabbitmq_connection = None
    consumer: TenantEventConsumer | None = None
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        app.state.rabbitmq_connection = connection
        logger.info("rabbitmq_connected", extra={"url": settings.rabbitmq_url})

        # Start cache-invalidation consumer if Redis is available
        if app.state.redis is not None:
            from app.services.cache_service import CacheService
            from app.domain.enums import UpstreamService

            cache = CacheService(app.state.redis)
            upstream_names = [u.value for u in UpstreamService]

            async def _on_invalidate(tenant_id: str) -> int:
                return await cache.invalidate_all_upstreams(tenant_id, upstream_names)

            consumer = TenantEventConsumer(connection, _on_invalidate)
            await consumer.start()
            logger.info("tenant_event_consumer_started")
    except Exception as exc:
        logger.warning(
            "rabbitmq_unavailable",
            extra={"url": settings.rabbitmq_url, "error": str(exc)},
        )

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    if consumer is not None:
        await consumer.stop()
    if app.state.rabbitmq_connection is not None:
        await app.state.rabbitmq_connection.close()
    if app.state.redis is not None:
        await close_redis_client(app.state.redis)
    await app.state.http_client.aclose()

    logger.info("gateway_shutdown", extra={"service": settings.app_name})


_docs_url = None if settings.environment == "production" else "/docs"
_redoc_url = None if settings.environment == "production" else "/redoc"
_openapi_url = None if settings.environment == "production" else "/openapi.json"

app = FastAPI(
    title="API Gateway",
    description=_DESCRIPTION,
    version=settings.app_version,
    contact={"name": "Platform Engineering", "email": "platform@nutratenant.io"},
    license_info={"name": "Proprietary"},
    openapi_tags=TAGS_METADATA,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
