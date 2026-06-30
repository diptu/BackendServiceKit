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
            upstream=UpstreamService.TENANT_MANAGEMENT,
            base_url=settings.tenant_management_base_url,
            cache_ttl=settings.redis_tenant_cache_ttl,
        ),
        Route(
            prefix="/api/v1/tenant-lifecycle",
            upstream=UpstreamService.TENANT_LIFECYCLE,
            base_url=settings.tenant_lifecycle_base_url,
            cache_ttl=settings.redis_lifecycle_cache_ttl,
        ),
        Route(
            prefix="/api/v1/provisioning",
            upstream=UpstreamService.TENANT_PROVISIONING,
            base_url=settings.tenant_provisioning_base_url,
            cache_ttl=settings.redis_provisioning_cache_ttl,
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
