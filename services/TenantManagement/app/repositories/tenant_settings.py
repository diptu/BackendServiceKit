"""Backward-compatibility shim — canonical definition moved to app.infrastructure.repositories.tenant_settings."""

from app.infrastructure.repositories.tenant_settings import TenantSettingsRepository

__all__ = ["TenantSettingsRepository"]
