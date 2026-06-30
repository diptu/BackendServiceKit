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
