"""Backward-compatibility shim — canonical definition moved to app.infrastructure.repositories.tenant_contact."""

from app.infrastructure.repositories.tenant_contact import TenantContactRepository

__all__ = ["TenantContactRepository"]
