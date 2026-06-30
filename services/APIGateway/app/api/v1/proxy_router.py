"""Catch-all reverse proxy — forwards every unmatched request to the appropriate upstream."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.core.openapi import RESPONSES_PROXY
from app.domain.exceptions import UpstreamTimeoutError, UpstreamUnavailableError
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.messaging.publisher import NullPublisher, RabbitMQPublisher
from app.services.cache_service import CacheService
from app.services.proxy_service import ProxyService
from app.services.route_service import RouteService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Proxy — TenantManagement", "Proxy — TenantLifecycle"])

_route_service = RouteService()


def _get_publisher(request: Request) -> RabbitMQPublisher | NullPublisher:
    conn = getattr(request.app.state, "rabbitmq_connection", None)
    if conn is not None and not conn.is_closed:
        return RabbitMQPublisher(conn)
    return NullPublisher()


@router.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
    include_in_schema=True,
    summary="Proxy request to upstream service",
    description=(
        "Routes the request to TenantManagement or TenantLifecycle based on the URL prefix. "
        "\n\n"
        "**Cached prefixes:**\n"
        "- `GET /api/v1/tenants/**` — cached 5 minutes\n"
        "- `GET /api/v1/tenant-lifecycle/**` — cached 60 seconds\n\n"
        "**Cache invalidation:** Any write (`POST`, `PUT`, `PATCH`, `DELETE`) that includes "
        "an `X-Tenant-ID` header purges all cached responses for that tenant."
    ),
    responses=RESPONSES_PROXY,
)
async def proxy(request: Request, full_path: str) -> Response:
    redis_client = get_redis(request)
    cache = CacheService(redis_client)
    publisher = _get_publisher(request)

    http_client: httpx.AsyncClient = request.app.state.http_client

    service = ProxyService(
        http_client=http_client,
        cache=cache,
        publisher=publisher,
        route_service=_route_service,
    )

    try:
        return await service.forward(request)
    except UpstreamTimeoutError as exc:
        logger.warning("upstream_timeout", extra={"upstream": exc.upstream})
        return JSONResponse(
            status_code=504,
            content={"detail": f"Upstream {exc.upstream!r} did not respond within {exc.timeout}s."},
        )
    except UpstreamUnavailableError as exc:
        logger.warning(
            "upstream_unavailable",
            extra={"upstream": exc.upstream, "detail": exc.detail},
        )
        return JSONResponse(
            status_code=503,
            content={"detail": f"Upstream {exc.upstream!r} is unavailable."},
        )
    except Exception as exc:
        logger.exception("proxy_unhandled_error", exc_info=exc)
        return JSONResponse(status_code=502, content={"detail": "Bad gateway."})
