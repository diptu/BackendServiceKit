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
    assert len(svc.routes) == 19


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


def test_resolve_observability_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/observability")
    assert route.upstream == UpstreamService.OBSERVABILITY_MANAGEMENT


def test_observability_route_is_never_cacheable(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/observability/dashboard")
    assert route.cacheable_methods == frozenset()


@pytest.mark.parametrize(
    "prefix",
    [
        "/api/v1/logs",
        "/api/v1/traces",
        "/api/v1/metrics",
        "/api/v1/monitoring",
        "/api/v1/alerts",
        "/api/v1/health",
        "/api/v1/observability",
    ],
)
def test_resolve_merged_service_prefixes(svc: RouteService, prefix: str) -> None:
    route = svc.resolve(prefix)
    assert route.upstream == UpstreamService.OBSERVABILITY_MANAGEMENT
    assert route.cacheable_methods == frozenset()
    assert route.cache_ttl == 0


def test_resolve_by_upstream_observability_management_returns_seven_routes(
    svc: RouteService,
) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.OBSERVABILITY_MANAGEMENT)
    assert len(routes) == 7
    prefixes = {r.prefix for r in routes}
    assert prefixes == {
        "/api/v1/logs",
        "/api/v1/traces",
        "/api/v1/metrics",
        "/api/v1/monitoring",
        "/api/v1/alerts",
        "/api/v1/health",
        "/api/v1/observability",
    }
    # all seven point at the same one base_url — one merged backend
    assert len({r.base_url for r in routes}) == 1


def test_resolve_organizations_root(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/organizations")
    assert route.upstream == UpstreamService.ORGANIZATION_MANAGEMENT


def test_organizations_route_is_never_cacheable(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/organizations/550e8400-e29b-41d4-a716-446655440000")
    assert route.cacheable_methods == frozenset()
    assert route.cache_ttl == 0


def test_resolve_by_upstream_organization_management_returns_one_route(
    svc: RouteService,
) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.ORGANIZATION_MANAGEMENT)
    assert len(routes) == 1
    assert routes[0].prefix == "/api/v1/organizations"


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


@pytest.mark.parametrize(
    "prefix",
    [
        "/api/v1/users",
        "/api/v1/roles",
        "/api/v1/permissions",
        "/api/v1/groups",
        "/api/v1/tenant-memberships",
        "/api/v1/entitlements",
        "/api/v1/access-reviews",
    ],
)
def test_resolve_iam_prefixes(svc: RouteService, prefix: str) -> None:
    route = svc.resolve(prefix)
    assert route.upstream == UpstreamService.IAM
    assert route.cacheable_methods == frozenset()
    assert route.cache_ttl == 0


def test_resolve_iam_users_sub_paths_route_to_iam(svc: RouteService) -> None:
    """/api/v1/users/{id}/roles and /api/v1/users/{id}/attributes are IAM's
    own sub-resources, not a separate registration — the single
    "/api/v1/users" prefix already covers them."""
    role_assignment = svc.resolve("/api/v1/users/550e8400-e29b-41d4-a716-446655440000/roles")
    assert role_assignment.upstream == UpstreamService.IAM

    attributes = svc.resolve("/api/v1/users/550e8400-e29b-41d4-a716-446655440000/attributes")
    assert attributes.upstream == UpstreamService.IAM


def test_tenant_memberships_does_not_collide_with_tenent(svc: RouteService) -> None:
    """/api/v1/tenant-memberships must route to IAM, not Tenent's
    /api/v1/tenants prefix — this is exactly the collision the rename from
    the README's literal /tenants/{id}/members path was made to avoid."""
    route = svc.resolve("/api/v1/tenant-memberships/550e8400-e29b-41d4-a716-446655440000/members")
    assert route.upstream == UpstreamService.IAM


def test_resolve_by_upstream_iam_returns_seven_routes(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.IAM)
    assert len(routes) == 7
    prefixes = {r.prefix for r in routes}
    assert prefixes == {
        "/api/v1/users",
        "/api/v1/roles",
        "/api/v1/permissions",
        "/api/v1/groups",
        "/api/v1/tenant-memberships",
        "/api/v1/entitlements",
        "/api/v1/access-reviews",
    }
    assert len({r.base_url for r in routes}) == 1
