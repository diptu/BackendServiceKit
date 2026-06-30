"""Gateway management endpoints — route registry, upstream health, cache stats."""

from __future__ import annotations

import logging
import time

import httpx
from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.gateway import (
    GatewayStatusResponse,
    RouteInfo,
    RoutesResponse,
    UpstreamHealth,
)
from app.services.route_service import RouteService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateway", tags=["Gateway"])

_route_service = RouteService()


@router.get(
    "/routes",
    response_model=RoutesResponse,
    summary="List registered routes",
    description="Returns all upstream routes the gateway can proxy to.",
)
async def list_routes() -> RoutesResponse:
    routes = _route_service.routes
    return RoutesResponse(
        routes=[
            RouteInfo(
                prefix=r.prefix,
                upstream=r.upstream.value,
                base_url=r.base_url,
                cacheable_methods=list(r.cacheable_methods),
                cache_ttl_seconds=r.cache_ttl,
            )
            for r in routes
        ],
        total=len(routes),
    )


@router.get(
    "/status",
    response_model=GatewayStatusResponse,
    summary="Gateway health status",
    description=(
        "Returns gateway status including Redis/RabbitMQ connectivity "
        "and a live health-check against each registered upstream."
    ),
)
async def gateway_status(request: Request) -> GatewayStatusResponse:
    redis_client = getattr(request.app.state, "redis", None)
    rabbitmq_conn = getattr(request.app.state, "rabbitmq_connection", None)

    redis_ok = False
    if redis_client is not None:
        try:
            redis_ok = bool(await redis_client.ping())
        except Exception:
            pass

    rabbitmq_ok = rabbitmq_conn is not None and not rabbitmq_conn.is_closed

    # Probe each upstream's /health endpoint
    upstream_results: list[UpstreamHealth] = []
    routes = _route_service.routes
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=5.0) as client:
        for route in routes:
            if route.upstream.value in seen:
                continue
            seen.add(route.upstream.value)
            health_url = f"{route.base_url}/health"
            t0 = time.monotonic()
            try:
                resp = await client.get(health_url)
                latency_ms = round((time.monotonic() - t0) * 1000, 2)
                upstream_results.append(
                    UpstreamHealth(
                        name=route.upstream.value,
                        base_url=route.base_url,
                        reachable=resp.is_success,
                        status_code=resp.status_code,
                        latency_ms=latency_ms,
                    )
                )
            except Exception as exc:
                upstream_results.append(
                    UpstreamHealth(
                        name=route.upstream.value,
                        base_url=route.base_url,
                        reachable=False,
                    )
                )
                logger.warning(
                    "upstream_health_check_failed",
                    extra={"upstream": route.upstream.value, "error": str(exc)},
                )

    return GatewayStatusResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
        redis_connected=redis_ok,
        rabbitmq_connected=rabbitmq_ok,
        upstreams=upstream_results,
    )
