"""Service wiring for the Traces domain."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends

from app.core.config import settings
from app.core.dependencies import get_http_client
from app.domains.tracing.infrastructure.tempo_client import TempoClient
from app.domains.tracing.services.trace_query_service import TraceQueryService


def get_tempo_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> TempoClient:
    return TempoClient(http_client, settings.tempo_base_url)


def get_trace_query_service(
    tempo_client: Annotated[TempoClient, Depends(get_tempo_client)],
) -> TraceQueryService:
    return TraceQueryService(tempo_client)
