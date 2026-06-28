"""Backward-compatibility shim — canonical definitions moved to app.infrastructure.repositories."""

from app.infrastructure.repositories.base import BaseRepository as BaseRepository
from app.infrastructure.repositories.base import PageResult as PageResult
from app.infrastructure.repositories.base import decode_cursor as decode_cursor
from app.infrastructure.repositories.base import encode_cursor as encode_cursor
from app.infrastructure.repositories.tenant import TenantFilter as TenantFilter
from app.infrastructure.repositories.tenant import TenantRepository as TenantRepository
from app.infrastructure.repositories.tenant_contact import (
    TenantContactRepository as TenantContactRepository,
)
from app.infrastructure.repositories.tenant_metadata import (
    TenantMetadataRepository as TenantMetadataRepository,
)
from app.infrastructure.repositories.tenant_settings import (
    TenantSettingsRepository as TenantSettingsRepository,
)
