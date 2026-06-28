"""Backward-compatibility shim — canonical definition moved to app.infrastructure.database.models.tenant."""

from app.infrastructure.database.models.tenant import Tenant

__all__ = ["Tenant"]
