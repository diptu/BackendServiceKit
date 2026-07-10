"""Tenant Resolver middleware — the access-layer half of Siloed multi-tenancy.

It turns the request's **subdomain** into a tenant (via the Tenent Control
Plane) before routing, and stashes it on `request.state.subdomain_tenant_id`.
The proxy handler then makes it authoritative:

- **Pre-auth requests** (e.g. `/api/v1/auth/login` at `acme.my-site.com`) get
  the subdomain's tenant forwarded as `X-Tenant-ID` — the client can't spoof
  which tenant it's logging into.
- **Authenticated requests** must have a JWT tenant that *matches* the
  subdomain's tenant, or they're rejected — a user can't reach tenant B's data
  by pointing a valid tenant-A token at `b.my-site.com`.

Fail-closed: an unknown subdomain is 404 and an unreachable Control Plane is
503 — the gateway never routes a request whose tenant it could not resolve.
This is opt-in (`tenant_resolver_enabled`); disabled, it is a pass-through.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.services.control_plane_client import (
    ControlPlaneClient,
    ControlPlaneUnavailableError,
)


class TenantMismatchError(Exception):
    """The authenticated tenant does not match the request's subdomain tenant."""


def extract_subdomain(host: str | None, base_domain: str | None, reserved: set[str]) -> str | None:
    """Return the tenant subdomain from a Host header, or None when there is
    nothing tenant-specific to resolve (apex domain, a reserved label like
    `www`, an unrelated host such as `localhost` or a raw IP)."""
    if not host or not base_domain:
        return None
    host = host.split(":", 1)[0].strip().lower()  # drop any port
    base = base_domain.strip().lower()
    if host == base or not host.endswith("." + base):
        return None
    label = host[: -(len(base) + 1)].split(".")[0]  # leftmost label
    if not label or label in reserved:
        return None
    return label


def reconcile_tenant(verified_tenant_id: str | None, subdomain_tenant_id: str | None) -> str | None:
    """Return the single authoritative tenant for the request. The JWT tenant
    wins when present; the subdomain tenant covers pre-auth requests. If both
    exist and disagree, raise — that's a cross-tenant access attempt."""
    if (
        verified_tenant_id is not None
        and subdomain_tenant_id is not None
        and verified_tenant_id != subdomain_tenant_id
    ):
        raise TenantMismatchError("Token tenant does not match the request subdomain.")
    return verified_tenant_id or subdomain_tenant_id


class TenantResolverMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.subdomain_tenant_id = None

        # Pass-through when disabled or on CORS preflight (no tenant needed).
        if not settings.tenant_resolver_enabled or request.method == "OPTIONS":
            return await call_next(request)

        subdomain = extract_subdomain(
            request.headers.get("host"),
            settings.gateway_base_domain,
            set(settings.tenant_resolver_reserved_subdomains),
        )
        if subdomain is None:
            return await call_next(request)

        client = getattr(request.app.state, "control_plane_client", None)
        if client is None:
            client = ControlPlaneClient(
                settings.control_plane_base_url,
                timeout=settings.control_plane_timeout,
                http_client=getattr(request.app.state, "http_client", None),
            )

        try:
            resolved = await client.resolve_subdomain(subdomain)
        except ControlPlaneUnavailableError:
            return JSONResponse(
                status_code=503,
                content={"detail": "Tenant routing is temporarily unavailable."},
            )

        if resolved is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Unknown tenant for subdomain '{subdomain}'."},
            )
        if resolved.status != "active":
            return JSONResponse(
                status_code=403,
                content={"detail": f"Tenant for subdomain '{subdomain}' is not active."},
            )

        request.state.subdomain_tenant_id = str(resolved.tenant_id)
        return await call_next(request)
