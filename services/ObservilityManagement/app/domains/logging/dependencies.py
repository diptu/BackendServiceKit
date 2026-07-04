"""Service wiring for the Logs domain."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends

from app.core.config import settings
from app.core.dependencies import get_http_client
from app.domains.logging.infrastructure.loki_client import LokiClient
from app.domains.logging.services.log_query_service import LogQueryService


def get_loki_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> LokiClient:
    return LokiClient(http_client, settings.loki_base_url)


def get_log_query_service(
    loki_client: Annotated[LokiClient, Depends(get_loki_client)],
) -> LogQueryService:
    return LogQueryService(loki_client)
