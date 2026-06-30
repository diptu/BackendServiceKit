"""Core reverse-proxy logic with Redis caching and RabbitMQ event emission."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.constants import (
    CACHEABLE_METHODS,
    GATEWAY_HEADER,
    HOP_BY_HOP_HEADERS,
    REQUEST_ID_HEADER,
    TENANT_ID_HEADER,
    WRITE_METHODS,
)
from app.core.config import settings
from app.domain.enums import CacheResult, UpstreamService
from app.domain.events import GatewayRequestCompleted, TenantCacheInvalidated
from app.domain.exceptions import (
    RouteNotFoundError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from app.services.cache_service import CacheService
from app.services.route_service import Route, RouteService

logger = logging.getLogger(__name__)

_ALL_UPSTREAM_NAMES = [u.value for u in UpstreamService]


class ProxyService:
    """Resolves routes, checks cache, forwards requests, and emits events.

    One instance is created per request (lightweight — shares the httpx client
    and cache service via injection from app.state / FastAPI dependencies).
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        cache: CacheService,
        publisher: Any,          # RabbitMQPublisher | NullPublisher
        route_service: RouteService,
    ) -> None:
        self._client = http_client
        self._cache = cache
        self._publisher = publisher
        self._routes = route_service

    async def forward(self, request: Request) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # Prefer the explicit header; fall back to the first UUID found in the path
        # so that write-triggered invalidation reaches keys cached without the header.
        tenant_id = request.headers.get(TENANT_ID_HEADER) or self._extract_tenant_from_path(
            request.url.path
        )
        path = request.url.path
        method = request.method.upper()
        started = time.monotonic()
        cache_result = CacheResult.SKIP

        # ── Route resolution ──────────────────────────────────────────────
        try:
            route = self._routes.resolve(path)
        except RouteNotFoundError:
            return JSONResponse(
                status_code=404,
                content={"detail": f"No upstream route found for path: {path!r}"},
            )

        # ── Cache lookup (GET only) ───────────────────────────────────────
        if method in CACHEABLE_METHODS:
            cache_key = CacheService.build_key(
                route.upstream.value, path, str(request.url.query)
            )
            raw, cache_result = await self._cache.get(cache_key)
            if raw is not None:
                status_code, headers, body = CacheService.decode_response(raw)
                headers[REQUEST_ID_HEADER] = request_id
                headers["X-Cache"] = "HIT"
                await self._emit_event(
                    request_id, method, path, route, status_code,
                    started, CacheResult.HIT, tenant_id,
                )
                return Response(content=body, status_code=status_code, headers=headers)

        # ── Forward to upstream ───────────────────────────────────────────
        path_with_query = request.url.path
        if request.url.query:
            path_with_query = f"{path_with_query}?{request.url.query}"
        upstream_url = route.upstream_url(path_with_query)
        forwarded_headers = self._build_upstream_headers(request, request_id)

        try:
            body_bytes = await request.body()
            upstream_resp = await self._client.request(
                method=method,
                url=upstream_url,
                headers=forwarded_headers,
                content=body_bytes,
                timeout=settings.upstream_timeout,
            )
        except httpx.TimeoutException:
            raise UpstreamTimeoutError(route.upstream.value, settings.upstream_timeout)
        except httpx.TransportError as exc:
            raise UpstreamUnavailableError(route.upstream.value, str(exc))

        # ── Cache the response (GET + 2xx only) ───────────────────────────
        response_headers = self._build_response_headers(upstream_resp, request_id)
        if (
            method in CACHEABLE_METHODS
            and upstream_resp.is_success
            and self._cache.available
        ):
            cache_key = CacheService.build_key(
                route.upstream.value, path, str(request.url.query)
            )
            encoded = CacheService.encode_response(
                upstream_resp.status_code,
                dict(response_headers),
                upstream_resp.content,
            )
            await self._cache.set(
                cache_key,
                encoded,
                route.cache_ttl,
                tenant_id=tenant_id,
                upstream=route.upstream.value,
            )
            cache_result = CacheResult.MISS

        # ── Cache invalidation on writes ──────────────────────────────────
        if method in WRITE_METHODS and upstream_resp.is_success and tenant_id:
            deleted = await self._cache.invalidate_all_upstreams(
                tenant_id, _ALL_UPSTREAM_NAMES
            )
            if deleted > 0:
                await self._publisher.publish(
                    "cache.tenant.invalidated",
                    TenantCacheInvalidated(
                        tenant_id=tenant_id,
                        triggered_by="write_request",
                        keys_deleted=deleted,
                    ),
                )

        # ── Dispatch Celery audit task ────────────────────────────────────
        self._dispatch_audit(request_id, method, path, route, upstream_resp.status_code, tenant_id)

        # ── Emit gateway event ────────────────────────────────────────────
        await self._emit_event(
            request_id, method, path, route, upstream_resp.status_code,
            started, cache_result, tenant_id,
        )

        response_headers["X-Cache"] = "MISS" if method in CACHEABLE_METHODS else "BYPASS"
        return Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=response_headers,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tenant_from_path(path: str) -> str | None:
        """Return the first UUID segment in the path, or None."""
        match = _UUID_RE.search(path)
        return match.group() if match else None

    def _build_upstream_headers(self, request: Request, request_id: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        for name, value in request.headers.items():
            if name.lower() not in HOP_BY_HOP_HEADERS:
                headers[name] = value
        headers[REQUEST_ID_HEADER] = request_id
        headers[GATEWAY_HEADER] = settings.app_version
        return headers

    def _build_response_headers(
        self, resp: httpx.Response, request_id: str
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        for name, value in resp.headers.items():
            if name.lower() not in HOP_BY_HOP_HEADERS:
                headers[name] = value
        headers[REQUEST_ID_HEADER] = request_id
        return headers

    def _dispatch_audit(
        self,
        request_id: str,
        method: str,
        path: str,
        route: Route,
        status_code: int,
        tenant_id: str | None,
    ) -> None:
        try:
            from app.tasks.audit_tasks import audit_request

            # apply_async with ignore_result avoids blocking on the broker / result backend.
            audit_request.apply_async(
                args=[
                    {
                        "request_id": request_id,
                        "method": method,
                        "path": path,
                        "upstream": route.upstream.value,
                        "status_code": status_code,
                        "tenant_id": tenant_id,
                    }
                ],
                ignore_result=True,
                retry=False,
            )
        except Exception as exc:
            logger.warning("audit_dispatch_failed", extra={"error": str(exc)})

    async def _emit_event(
        self,
        request_id: str,
        method: str,
        path: str,
        route: Route,
        status_code: int,
        started: float,
        cache_result: CacheResult,
        tenant_id: str | None,
    ) -> None:
        latency_ms = round((time.monotonic() - started) * 1000, 2)
        event = GatewayRequestCompleted(
            request_id=request_id,
            method=method,
            path=path,
            upstream=route.upstream.value,
            status_code=status_code,
            latency_ms=latency_ms,
            cache_result=cache_result.value,
            tenant_id=tenant_id,
        )
        await self._publisher.publish("gateway.request.completed", event)
        logger.info(
            "request_proxied",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "upstream": route.upstream.value,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "cache": cache_result.value,
            },
        )
