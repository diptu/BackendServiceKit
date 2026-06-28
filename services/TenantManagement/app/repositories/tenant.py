"""Backward-compatibility shim — canonical definition moved to app.infrastructure.repositories.tenant."""

from app.infrastructure.repositories.tenant import TenantFilter, TenantRepository

__all__ = ["TenantFilter", "TenantRepository"]
