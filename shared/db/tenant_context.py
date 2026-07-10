"""The current request's tenant, carried in a ContextVar.

In the north-star flow the gateway resolves a subdomain to a tenant and a
Tenant Resolver middleware stamps it here once per request; `get_db` then
reads it. `get_current_tenant()` **fails closed** — an unset tenant raises
rather than silently falling back to any shared/default database.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import UUID

_current_tenant: ContextVar[UUID | None] = ContextVar("current_tenant_id", default=None)


class TenantContextError(RuntimeError):
    """Raised when a tenant-scoped operation runs with no tenant in context."""


def set_current_tenant(tenant_id: UUID) -> Token[UUID | None]:
    """Set the current tenant; returns a token to restore the previous value."""
    return _current_tenant.set(tenant_id)


def reset_current_tenant(token: Token[UUID | None]) -> None:
    _current_tenant.reset(token)


def get_current_tenant() -> UUID:
    tenant_id = _current_tenant.get()
    if tenant_id is None:
        raise TenantContextError(
            "No tenant in context — refusing to open a database session (fail closed)."
        )
    return tenant_id


def current_tenant_or_none() -> UUID | None:
    return _current_tenant.get()
