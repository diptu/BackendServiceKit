"""Tenant-scope enforcement + service wiring for the logs API.

No endpoint may build a Loki query without going through `CallerScope` first
— it is the single place `tenant_id` is extracted and validated before any
LogQL gets built (see services/Logging/TODO.md, Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

import httpx
from fastapi import Depends, Request

from app.core.config import settings
from app.domain.exceptions import CrossTenantAccessError, MissingTenantScopeError
from app.infrastructure.loki.loki_client import LokiClient
from app.middleware.auth import verify_token
from app.services.log_export_service import LogExportService
from app.services.log_ingest_service import LogIngestService
from app.services.log_query_service import LogQueryService

PLATFORM_ADMIN_ROLE = "platform-admin"
TENANT_ID_HEADER = "X-Tenant-ID"


@dataclass(frozen=True)
class CallerScope:
    tenant_id: str | None
    is_platform_admin: bool


async def get_caller_scope(
    request: Request,
    claims: Annotated[dict[str, Any], Depends(verify_token)],
) -> CallerScope:
    tenant_id = claims.get("tenant_id") or request.headers.get(TENANT_ID_HEADER)
    roles = claims.get("roles") or []
    return CallerScope(tenant_id=tenant_id, is_platform_admin=PLATFORM_ADMIN_ROLE in roles)


async def require_tenant_scope(
    scope: Annotated[CallerScope, Depends(get_caller_scope)],
) -> CallerScope:
    """Every /logs read endpoint depends on this — guarantees a scope exists."""
    if not scope.tenant_id and not scope.is_platform_admin:
        raise MissingTenantScopeError()
    return scope


async def require_platform_admin(
    scope: Annotated[CallerScope, Depends(get_caller_scope)],
) -> CallerScope:
    """Cross-tenant endpoints (e.g. `/logs/service/{service}`) require this."""
    if not scope.is_platform_admin:
        raise CrossTenantAccessError("Platform-admin role required for cross-tenant queries.")
    return scope


def check_tenant_access(scope: CallerScope, requested_tenant_id: str) -> None:
    """Raise unless the caller owns `requested_tenant_id` or is a platform admin."""
    if scope.is_platform_admin:
        return
    if scope.tenant_id != requested_tenant_id:
        raise CrossTenantAccessError()


def get_loki_client(request: Request) -> LokiClient:
    http_client: httpx.AsyncClient = request.app.state.http_client
    return LokiClient(http_client, settings.loki_base_url)


def get_query_service(loki: Annotated[LokiClient, Depends(get_loki_client)]) -> LogQueryService:
    return LogQueryService(loki)


def get_ingest_service(loki: Annotated[LokiClient, Depends(get_loki_client)]) -> LogIngestService:
    return LogIngestService(loki, max_bulk_items=settings.logs_bulk_max_items)


def get_export_service(
    query_service: Annotated[LogQueryService, Depends(get_query_service)],
) -> LogExportService:
    return LogExportService(query_service)
