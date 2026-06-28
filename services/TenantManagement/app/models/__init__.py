"""Backward-compatibility shim — canonical definitions moved to app.infrastructure.database.models."""

from app.infrastructure.database.models import (
    Tenant,
    TenantContact,
    TenantMetadata,
    TenantSettings,
)

__all__ = ["Tenant", "TenantContact", "TenantMetadata", "TenantSettings"]
