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
    assert len(svc.routes) == 26


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
        "/api/v1/roles",
        "/api/v1/permissions",
        "/api/v1/groups",
        "/api/v1/tenant-memberships",
        "/api/v1/entitlements",
        "/api/v1/access-reviews",
        "/api/v1/user-attributes",
        "/api/v1/user-roles",
        "/api/v1/policies",
        "/api/v1/authorization",
    ],
)
def test_resolve_iam_prefixes(svc: RouteService, prefix: str) -> None:
    route = svc.resolve(prefix)
    assert route.upstream == UpstreamService.IAM
    assert route.cacheable_methods == frozenset()
    assert route.cache_ttl == 0


@pytest.mark.parametrize(
    "prefix", ["/api/v1/users", "/api/v1/platform-invitations", "/api/v1/profiles"]
)
def test_resolve_user_prefixes(svc: RouteService, prefix: str) -> None:
    route = svc.resolve(prefix)
    assert route.upstream == UpstreamService.USER
    assert route.cacheable_methods == frozenset()
    assert route.cache_ttl == 0


def test_resolve_authentication_prefix(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/auth")
    assert route.upstream == UpstreamService.AUTHENTICATION
    assert route.base_url == "http://localhost:8024"
    assert route.cacheable_methods == frozenset()
    assert route.cache_ttl == 0


def test_resolve_users_sub_paths_route_to_user(svc: RouteService) -> None:
    """/api/v1/users/{id} sub-paths route to User (the merged
    UserManagement + UserLifecycleManagement + UserProfileManagement
    service — see services/User/TODO.md), not IAM. IAM's own
    attribute-assignment and role-assignment sub-resources were renamed to
    /api/v1/user-attributes/{id} and /api/v1/user-roles/{id} specifically
    to avoid being swallowed by this prefix (plain string matching, no
    path templating). The role-assignment rename was a real, previously
    undetected gap: roles_router.py defines that path inline with no
    router-level prefix=, so the original /api/v1/users repoint missed it
    — /api/v1/users/{id}/roles was silently routing to UserManagement (a
    404) until this was found and fixed. Status-lifecycle transitions
    (lock/unlock/restore/onboard/offboard) live directly under
    /api/v1/users/{id}/... now too — the merge removed the reason a
    separate /api/v1/user-lifecycle prefix ever existed."""
    sub_path = svc.resolve("/api/v1/users/550e8400-e29b-41d4-a716-446655440000/activate")
    assert sub_path.upstream == UpstreamService.USER

    lock = svc.resolve("/api/v1/users/550e8400-e29b-41d4-a716-446655440000/lock")
    assert lock.upstream == UpstreamService.USER

    attributes = svc.resolve("/api/v1/user-attributes/550e8400-e29b-41d4-a716-446655440000")
    assert attributes.upstream == UpstreamService.IAM

    roles = svc.resolve("/api/v1/user-roles/550e8400-e29b-41d4-a716-446655440000")
    assert roles.upstream == UpstreamService.IAM


def test_resolve_profiles_sub_paths(svc: RouteService) -> None:
    route = svc.resolve("/api/v1/profiles/550e8400-e29b-41d4-a716-446655440000/preferences")
    assert route.upstream == UpstreamService.USER


def test_tenant_memberships_does_not_collide_with_tenent(svc: RouteService) -> None:
    """/api/v1/tenant-memberships must route to IAM, not Tenent's
    /api/v1/tenants prefix — this is exactly the collision the rename from
    the README's literal /tenants/{id}/members path was made to avoid."""
    route = svc.resolve("/api/v1/tenant-memberships/550e8400-e29b-41d4-a716-446655440000/members")
    assert route.upstream == UpstreamService.IAM


def test_resolve_by_upstream_iam_returns_ten_routes(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.IAM)
    assert len(routes) == 10
    prefixes = {r.prefix for r in routes}
    assert prefixes == {
        "/api/v1/roles",
        "/api/v1/permissions",
        "/api/v1/groups",
        "/api/v1/tenant-memberships",
        "/api/v1/entitlements",
        "/api/v1/access-reviews",
        "/api/v1/user-attributes",
        "/api/v1/user-roles",
        "/api/v1/policies",
        "/api/v1/authorization",
    }
    assert len({r.base_url for r in routes}) == 1


def test_resolve_by_upstream_user_returns_three_routes(svc: RouteService) -> None:
    routes = svc.resolve_by_upstream(UpstreamService.USER)
    assert len(routes) == 3
    prefixes = {r.prefix for r in routes}
    assert prefixes == {"/api/v1/users", "/api/v1/platform-invitations", "/api/v1/profiles"}
    assert len({r.base_url for r in routes}) == 1
