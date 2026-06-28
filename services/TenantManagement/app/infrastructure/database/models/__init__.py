"""ORM models for the Tenant Management Service.

Import all models here so Alembic autogenerate can discover them.
"""

from app.infrastructure.database.models.tenant import Tenant
from app.infrastructure.database.models.tenant_contact import TenantContact
from app.infrastructure.database.models.tenant_metadata import TenantMetadata
from app.infrastructure.database.models.tenant_settings import TenantSettings

__all__ = ["Tenant", "TenantContact", "TenantMetadata", "TenantSettings"]
