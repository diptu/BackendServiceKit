"""Gateway management endpoints — route registry, upstream health, cache stats, Kong integration."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.schemas.gateway import (
    GatewayStatusResponse,
    KongPluginInfo,
    KongRouteInfo,
    KongServiceInfo,
    KongStatusResponse,
    KongSyncResponse,
    RouteInfo,
    RoutesResponse,
    UpstreamHealth,
)
from app.services.kong_admin_service import KongAdminService
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


# ── Kong integration endpoints ─────────────────────────────────────────────


@router.get(
    "/kong/status",
    response_model=KongStatusResponse,
    tags=["Kong"],
    summary="Kong node status",
    description=(
        "Query the Kong Admin API for node info (connections, memory, worker states). "
        "Returns `available=false` if Kong is unreachable — does not raise an error."
    ),
)
async def kong_status(request: Request) -> KongStatusResponse:
    svc = KongAdminService(http_client=request.app.state.http_client)
    try:
        status_data, services, routes, plugins = await asyncio.gather(
            svc.get_status(),
            svc.list_services(),
            svc.list_routes(),
            svc.list_plugins(),
        )
        return KongStatusResponse(
            available=True,
            version=status_data.get("version"),
            hostname=status_data.get("hostname"),
            database="off",
            services_count=len(services),
            routes_count=len(routes),
            plugins_count=len(plugins),
        )
    except Exception:
        return KongStatusResponse(available=False)


@router.get(
    "/kong/services",
    response_model=list[KongServiceInfo],
    tags=["Kong"],
    summary="List Kong services",
    description="Return all upstream services registered with Kong.",
)
async def kong_services(request: Request) -> list[KongServiceInfo]:
    svc = KongAdminService(http_client=request.app.state.http_client)
    try:
        raw = await svc.list_services()
        return [
            KongServiceInfo(
                id=s["id"],
                name=s["name"],
                host=s.get("host"),
                port=s.get("port"),
                protocol=s.get("protocol"),
                tags=s.get("tags") or [],
            )
            for s in raw
        ]
    except httpx.TransportError:
        raise HTTPException(status_code=503, detail="Kong Admin API is unreachable.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Kong Admin API returned {exc.response.status_code}.",
        )


@router.get(
    "/kong/routes",
    response_model=list[KongRouteInfo],
    tags=["Kong"],
    summary="List Kong routes",
    description="Return all routes registered with Kong.",
)
async def kong_routes(request: Request) -> list[KongRouteInfo]:
    svc = KongAdminService(http_client=request.app.state.http_client)
    try:
        raw = await svc.list_routes()
        return [
            KongRouteInfo(
                id=r["id"],
                name=r.get("name"),
                paths=r.get("paths"),
                protocols=r.get("protocols") or [],
                tags=r.get("tags") or [],
            )
            for r in raw
        ]
    except httpx.TransportError:
        raise HTTPException(status_code=503, detail="Kong Admin API is unreachable.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Kong Admin API returned {exc.response.status_code}.",
        )


@router.get(
    "/kong/plugins",
    response_model=list[KongPluginInfo],
    tags=["Kong"],
    summary="List active Kong plugins",
    description="Return all plugins (global, service-scoped, and route-scoped).",
)
async def kong_plugins(request: Request) -> list[KongPluginInfo]:
    svc = KongAdminService(http_client=request.app.state.http_client)
    try:
        raw = await svc.list_plugins()
        return [
            KongPluginInfo(
                id=p["id"],
                name=p["name"],
                enabled=p.get("enabled", True),
                tags=p.get("tags") or [],
            )
            for p in raw
        ]
    except httpx.TransportError:
        raise HTTPException(status_code=503, detail="Kong Admin API is unreachable.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Kong Admin API returned {exc.response.status_code}.",
        )


@router.post(
    "/kong/sync",
    response_model=KongSyncResponse,
    status_code=200,
    tags=["Kong"],
    summary="Sync FastAPI route registry into Kong",
    description=(
        "Upserts all routes from the FastAPI route registry into Kong via the Admin API. "
        "Idempotent — safe to call multiple times. "
        "Returns counts of synced, skipped, and failed prefixes."
    ),
)
async def kong_sync(request: Request) -> KongSyncResponse:
    svc = KongAdminService(http_client=request.app.state.http_client)
    try:
        result = await svc.sync_routes()
        return KongSyncResponse(
            synced=result.synced,
            skipped=result.skipped,
            failed=result.failed,
            total=result.total,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Kong sync failed: {exc}")
