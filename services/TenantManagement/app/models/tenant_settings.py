"""Backward-compatibility shim — canonical definition moved to app.infrastructure.database.models.tenant_settings."""

from app.infrastructure.database.models.tenant_settings import TenantSettings

__all__ = ["TenantSettings"]
