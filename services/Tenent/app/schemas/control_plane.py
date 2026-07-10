"""Pydantic schemas for the Control Plane registry endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import TenantConnectionStatus
from app.schemas.base import AppBaseModel


class RegisterConnectionRequest(AppBaseModel):
    """tenant_id comes from the path. A password is never accepted here —
    only a `secret_ref` pointing at a secrets backend."""

    subdomain: str = Field(..., min_length=1, max_length=63)
    db_host: str = Field(..., min_length=1, max_length=255)
    db_name: str = Field(..., min_length=1, max_length=255)
    db_user: str = Field(..., min_length=1, max_length=255)
    db_driver: str = Field(default="postgresql+asyncpg", max_length=64)
    db_port: int = Field(default=5432, ge=1, le=65535)
    secret_ref: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=100)
    status: TenantConnectionStatus = TenantConnectionStatus.PROVISIONING


class ConnectionResponse(AppBaseModel):
    """Non-secret view of a Control Plane record — safe to return to internal
    callers. Never carries a password (none is stored)."""

    tenant_id: UUID
    subdomain: str
    db_driver: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    secret_ref: str | None = None
    region: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class SubdomainResolveResponse(AppBaseModel):
    """What the gateway's Tenant Resolver needs — a subdomain mapped to a
    tenant. No connection coordinates, no credentials."""

    tenant_id: UUID
    subdomain: str
    status: str


class DsnResponse(AppBaseModel):
    """The assembled connection string. Internal-only — this carries a live
    credential; it must never be exposed through the public gateway."""

    dsn: str
