"""Tenant-aware database routing for Siloed (database-per-tenant)
multi-tenancy.

This package is the single, audited implementation of "which physical
database does this request's tenant use" — built once here so every
data-owning service (IAM first, then User / Organization / Authentication)
consumes the same router instead of re-deriving connection routing per
service. See services/IAM/TODO.md → "Siloed Multi-tenancy Migration
Standard".

Layers:
- `resolver`  — tenant_id → connection string (a stand-in for the Tenent-owned
                Control Plane; swappable without touching callers).
- `registry`  — connection string → cached per-tenant AsyncEngine/session.
- `tenant_context` — the current request's tenant, for the resolver-driven
                (subdomain → context) path.
"""

from __future__ import annotations

from shared.db.registry import TenantEngineRegistry
from shared.db.resolver import (
    ControlPlaneConnectionResolver,
    ControlPlaneUnavailableError,
    TemplateConnectionResolver,
    TenantConnectionResolver,
)
from shared.db.tenant_context import (
    TenantContextError,
    current_tenant_or_none,
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
)

__all__ = [
    "ControlPlaneConnectionResolver",
    "ControlPlaneUnavailableError",
    "TemplateConnectionResolver",
    "TenantConnectionResolver",
    "TenantContextError",
    "TenantEngineRegistry",
    "current_tenant_or_none",
    "get_current_tenant",
    "reset_current_tenant",
    "set_current_tenant",
]
