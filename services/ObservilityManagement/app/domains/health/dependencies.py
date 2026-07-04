"""Service wiring for the Health domain."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import Depends

from app.core.dependencies import get_http_client
from app.domains.health.infrastructure.target_client import TargetClient
from app.domains.health.services.health_service import HealthService
from app.domains.health.services.uptime_tracker import UptimeTracker

_uptime_tracker = UptimeTracker()


def get_target_client(
    http_client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> TargetClient:
    return TargetClient(http_client)


def get_health_service(
    target_client: Annotated[TargetClient, Depends(get_target_client)],
) -> HealthService:
    return HealthService(target_client, _uptime_tracker)
