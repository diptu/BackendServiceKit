"""Operator-only access control + service wiring for the traces API.

Unlike Logging's `require_tenant_scope` (which exists per-endpoint because
some endpoints are tenant-scoped and some are platform-admin-only), this
service has a single uniform access tier — see TODO.md Decision #3 for why
there is no tenant-self-service model here. `require_operator_scope` is
applied once, at router level, in `traces_router.py`.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import Depends, Request

from app.core.config import settings
from app.domain.exceptions import NotAnOperatorError
from app.infrastructure.tempo.tempo_client import TempoClient
from app.middleware.auth import verify_token
from app.services.trace_export_service import TraceExportService
from app.services.trace_query_service import TraceQueryService

PLATFORM_ADMIN_ROLE = "platform-admin"


async def require_operator_scope(
    claims: Annotated[dict[str, Any], Depends(verify_token)],
) -> None:
    """Gates every /traces endpoint. No-op when jwt_auth_enabled=False."""
    if not settings.jwt_auth_enabled:
        return
    roles = claims.get("roles") or []
    if PLATFORM_ADMIN_ROLE not in roles:
        raise NotAnOperatorError()


def get_tempo_client(request: Request) -> TempoClient:
    http_client: httpx.AsyncClient = request.app.state.http_client
    return TempoClient(http_client, settings.tempo_base_url)


def get_query_service(
    tempo: Annotated[TempoClient, Depends(get_tempo_client)],
) -> TraceQueryService:
    return TraceQueryService(tempo)


def get_export_service(
    query_service: Annotated[TraceQueryService, Depends(get_query_service)],
) -> TraceExportService:
    return TraceExportService(query_service)
