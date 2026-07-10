"""Catch-all reverse proxy — forwards every unmatched request to the appropriate upstream."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.core.openapi import RESPONSES_PROXY
from app.domain.exceptions import (
    GatewayTokenInvalidError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.messaging.publisher import NullPublisher, RabbitMQPublisher
from app.middleware.tenant_resolver import TenantMismatchError, reconcile_tenant
from app.services.cache_service import CacheService
from app.services.proxy_service import ProxyService
from app.services.route_service import RouteService
from app.services.token_verifier import verify_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Proxy — Tenent", "Proxy — TenantProvisioning"])

_route_service = RouteService()

# Authentication's own routes are exempt from this gate — /login, /refresh,
# /credentials, /introspect, /password/forgot and /password/reset all have
# to be reachable *without* an existing valid access token (that's the
# whole point of them), and the routes among these that do need to act on
# "the current user" (/logout-all, /password/change, /sessions/*, /events)
# are already guarded by Authentication's own CurrentSubjectDep — gating
# them here too would be redundant, not additional safety.
_AUTH_EXEMPT_PREFIX = "/api/v1/auth"


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    return header[len("bearer ") :].strip() or None


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
        "Routes the request to the Tenent combined service or TenantProvisioning based on the URL prefix.\n\n"
        "**Cached prefixes:**\n"
        "- `GET /api/v1/tenants/**` — cached 5 minutes\n"
        "- `GET /api/v1/lifecycle/**` — cached 5 minutes\n"
        "- `GET /api/v1/isolation/**` — cached 60 seconds\n"
        "- `GET /api/v1/provisioning/**` — cached 30 seconds\n\n"
        "**Cache invalidation:** Any write (`POST`, `PUT`, `PATCH`, `DELETE`) that includes "
        "an `X-Tenant-ID` header purges all cached responses for that tenant."
    ),
    responses=RESPONSES_PROXY,
)
async def proxy(request: Request, full_path: str) -> Response:
    path = request.url.path
    verified_tenant_id: str | None = None

    if not (path == _AUTH_EXEMPT_PREFIX or path.startswith(_AUTH_EXEMPT_PREFIX + "/")):
        token = _bearer_token(request)
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="Authorization: Bearer <access_token> is required.",
            )
        try:
            identity = verify_access_token(token)
        except GatewayTokenInvalidError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        verified_tenant_id = str(identity["tenant_id"])

    # Reconcile the verified JWT tenant with the subdomain-resolved tenant that
    # the Tenant Resolver middleware set (None when the feature is off / no
    # subdomain). The JWT wins when present; the subdomain covers pre-auth
    # routes; a mismatch is a cross-tenant access attempt.
    subdomain_tenant_id = getattr(request.state, "subdomain_tenant_id", None)
    try:
        authoritative_tenant_id = reconcile_tenant(verified_tenant_id, subdomain_tenant_id)
    except TenantMismatchError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

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
        return await service.forward(request, verified_tenant_id=authoritative_tenant_id)
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
