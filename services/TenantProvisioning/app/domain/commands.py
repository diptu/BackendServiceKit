"""Command DTOs — the input side of service methods."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProvisionTenantCmd:
    tenant_id: UUID
    subdomain: str
    region: str | None = None
