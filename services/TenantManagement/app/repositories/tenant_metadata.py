"""Backward-compatibility shim — canonical definition moved to app.infrastructure.repositories.tenant_metadata."""

from app.infrastructure.repositories.tenant_metadata import TenantMetadataRepository

__all__ = ["TenantMetadataRepository"]
