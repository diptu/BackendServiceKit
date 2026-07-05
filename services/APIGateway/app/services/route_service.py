"""Route registry — maps URL prefixes to upstream microservices."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.core.constants import CACHEABLE_METHODS
from app.domain.enums import UpstreamService
from app.domain.exceptions import RouteNotFoundError


@dataclass(frozen=True)
class Route:
    """Describes how a URL prefix maps to an upstream service."""

    prefix: str                          # e.g. "/api/v1/tenants"
    upstream: UpstreamService
    base_url: str                        # upstream origin, no trailing slash
    cacheable_methods: frozenset[str] = field(default_factory=lambda: CACHEABLE_METHODS)
    cache_ttl: int = 300                 # seconds

    def matches(self, path: str) -> bool:
        return path == self.prefix or path.startswith(self.prefix + "/")

    def upstream_url(self, path: str) -> str:
        """Build the full upstream URL for the given gateway path."""
        return f"{self.base_url.rstrip('/')}{path}"


def _build_registry() -> list[Route]:
    return [
        Route(
            prefix="/api/v1/tenants",
            upstream=UpstreamService.TENENT,
            base_url=settings.tenent_base_url,
            cache_ttl=settings.redis_tenent_cache_ttl,
        ),
        Route(
            prefix="/api/v1/lifecycle",
            upstream=UpstreamService.TENENT,
            base_url=settings.tenent_base_url,
            cache_ttl=settings.redis_tenent_cache_ttl,
        ),
        Route(
            prefix="/api/v1/isolation",
            upstream=UpstreamService.TENENT,
            base_url=settings.tenent_base_url,
            cache_ttl=settings.redis_isolation_cache_ttl,
        ),
        Route(
            prefix="/api/v1/provisioning",
            upstream=UpstreamService.TENANT_PROVISIONING,
            base_url=settings.tenant_provisioning_base_url,
            cache_ttl=settings.redis_provisioning_cache_ttl,
        ),
        # Seven prefixes, one upstream — services/ObservilityManagement/
        # merges what used to be seven separate deployables (Logging,
        # DistributedTracing, MetricsCollection, Monitoring, Alerting,
        # Observability, HealthCheck) into one container. See
        # services/ObservilityManagement/TODO.md Decision #1/#6: the URL
        # surface is preserved exactly, only the backend count changed
        # from seven to one — gateway_status's dedup-by-upstream logic
        # now correctly probes this one container's health once instead
        # of seven redundant times.
        Route(
            prefix="/api/v1/logs",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            prefix="/api/v1/traces",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            prefix="/api/v1/metrics",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            prefix="/api/v1/monitoring",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            prefix="/api/v1/alerts",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            # Must be "/api/v1/health" exactly, matching
            # ObservilityManagement's real mounted path — the gateway
            # forwards the incoming path unmodified (Route.upstream_url),
            # it does not rewrite prefixes.
            prefix="/api/v1/health",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            # Never cacheable — investigation/correlation data is
            # meaningless if stale.
            prefix="/api/v1/observability",
            upstream=UpstreamService.OBSERVABILITY_MANAGEMENT,
            base_url=settings.observability_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
        Route(
            # Not cacheable — unlike Tenent's routes, OrganizationManagement
            # has no domain-event publisher wiring writes into a cache
            # invalidation yet, so caching GETs here would risk serving
            # stale data after an update/delete with nothing to bust it.
            prefix="/api/v1/organizations",
            upstream=UpstreamService.ORGANIZATION_MANAGEMENT,
            base_url=settings.organization_management_base_url,
            cacheable_methods=frozenset(),
            cache_ttl=0,
        ),
    ]


class RouteService:
    """Resolves incoming paths to their registered upstream route."""

    def __init__(self) -> None:
        self._routes: list[Route] = _build_registry()

    @property
    def routes(self) -> list[Route]:
        return list(self._routes)

    def resolve(self, path: str) -> Route:
        """Return the first matching route or raise RouteNotFoundError."""
        for route in self._routes:
            if route.matches(path):
                return route
        raise RouteNotFoundError(path)

    def resolve_by_upstream(self, upstream: UpstreamService) -> list[Route]:
        return [r for r in self._routes if r.upstream == upstream]
