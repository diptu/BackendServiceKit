"""Response schemas for gateway management endpoints."""

from __future__ import annotations

from app.schemas.base import AppBaseModel


class RouteInfo(AppBaseModel):
    prefix: str
    upstream: str
    base_url: str
    cacheable_methods: list[str]
    cache_ttl_seconds: int


class RoutesResponse(AppBaseModel):
    routes: list[RouteInfo]
    total: int


class UpstreamHealth(AppBaseModel):
    name: str
    base_url: str
    reachable: bool
    status_code: int | None = None
    latency_ms: float | None = None


class GatewayStatusResponse(AppBaseModel):
    status: str
    version: str
    environment: str
    redis_connected: bool
    rabbitmq_connected: bool
    upstreams: list[UpstreamHealth]


class HealthResponse(AppBaseModel):
    status: str


class ReadyResponse(AppBaseModel):
    status: str
    redis: str
    rabbitmq: str


class KongServiceInfo(AppBaseModel):
    id: str
    name: str
    host: str | None = None
    port: int | None = None
    protocol: str | None = None
    tags: list[str] = []


class KongRouteInfo(AppBaseModel):
    id: str
    name: str | None = None
    paths: list[str] | None = None
    protocols: list[str] = []
    tags: list[str] = []


class KongPluginInfo(AppBaseModel):
    id: str
    name: str
    enabled: bool
    tags: list[str] = []


class KongStatusResponse(AppBaseModel):
    available: bool
    version: str | None = None
    hostname: str | None = None
    database: str = "off"
    services_count: int = 0
    routes_count: int = 0
    plugins_count: int = 0


class KongSyncResponse(AppBaseModel):
    synced: list[str]
    skipped: list[str]
    failed: list[str]
    total: int
