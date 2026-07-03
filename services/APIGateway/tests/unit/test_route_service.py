"""Unit tests for RouteService — route resolution logic."""

from __future__ import annotations

import pytest

from app.domain.enums import UpstreamService
from app.domain.exceptions import RouteNotFoundError
from app.services.route_service import RouteService


@pytest.fixture
def svc() -> RouteService:
    return RouteService()


def test_routes_are_registered(svc: RouteService) -> None:
    assert len(svc.routes) == 7


def test_resolve_tenants_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/tenants")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_tenants_sub_path(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/tenants/550e8400-e29b-41d4-a716-446655440000")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_tenants_nested(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/tenants/abc/settings")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_lifecycle_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/lifecycle")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_lifecycle_sub_path(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/lifecycle/550e8400-e29b-41d4-a716-446655440000/history")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_isolation_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/isolation")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_isolation_sub_path(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/isolation/validate")
    assert route.upstream == UpstreamService.TENENT


def test_resolve_provisioning_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/provisioning")
    assert route.upstream == UpstreamService.TENANT_PROVISIONING


def test_resolve_logs_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/logs")
    assert route.upstream == UpstreamService.LOGGING


def test_logs_route_is_never_cacheable(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/logs/search")
    assert route.cacheable_methods == frozenset()


def test_resolve_unknown_path_raises(svc: RouteService) -> None:
    with pytest.raises(RouteNotFoundError) as exc_info:
        svc.resolve("/api/v1/unknown-service/foo")
    assert "/api/v1/unknown-service/foo" in str(exc_info.value)


def test_resolve_by_upstream_tenent_returns_three_routes(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.TENENT)
    assert len(routes) == 3
    prefixes = {r.prefix for r in routes}
    assert prefixes == {"/api/v1/tenants", "/api/v1/lifecycle", "/api/v1/isolation"}


def test_resolve_by_upstream_provisioning_returns_one_route(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.TENANT_PROVISIONING)
    assert len(routes) == 1
    assert routes[0].prefix == "/api/v1/provisioning"


def test_resolve_by_upstream_logging_returns_one_route(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.LOGGING)
    assert len(routes) == 1
    assert routes[0].prefix == "/api/v1/logs"


def test_resolve_traces_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/traces")
    assert route.upstream == UpstreamService.DISTRIBUTED_TRACING


def test_traces_route_is_never_cacheable(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/traces/search")
    assert route.cacheable_methods == frozenset()


def test_resolve_by_upstream_distributed_tracing_returns_one_route(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.DISTRIBUTED_TRACING)
    assert len(routes) == 1
    assert routes[0].prefix == "/api/v1/traces"


def test_resolve_metrics_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/metrics")
    assert route.upstream == UpstreamService.METRICS_COLLECTION


def test_metrics_route_is_never_cacheable(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/metrics/query")
    assert route.cacheable_methods == frozenset()


def test_resolve_by_upstream_metrics_collection_returns_one_route(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.METRICS_COLLECTION)
    assert len(routes) == 1
    assert routes[0].prefix == "/api/v1/metrics"


def test_upstream_url_builds_correctly(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/tenants/abc")
    url = route.upstream_url("/api/v1/tenants/abc")
    assert url.endswith("/api/v1/tenants/abc")
    assert "localhost" in url or "http" in url


def test_health_path_does_not_match_any_route(svc: RouteService) -> None:
    with pytest.raises(RouteNotFoundError):
        svc.resolve("/health")


def test_gateway_path_does_not_match_any_route(svc: RouteService) -> None:
    with pytest.raises(RouteNotFoundError):
        svc.resolve("/api/v1/gateway/routes")


def test_old_tenant_lifecycle_prefix_no_longer_routed(svc: RouteService) -> None:
    with pytest.raises(RouteNotFoundError):
        svc.resolve("/api/v1/tenant-lifecycle/abc")
