"""Reshapes Alerting's real alert list into Incidents — TODO.md Decision #6."""

from __future__ import annotations

from app.domain.observability import Incident
from app.infrastructure.siblings.alerting_client import AlertingClient
from app.repositories.incident_repository import group_into_incidents


class IncidentService:
    def __init__(self, alerting_client: AlertingClient) -> None:
        self._alerting = alerting_client

    async def list_incidents(self) -> list[Incident]:
        raw_alerts = await self._alerting.list_alerts()
        if not raw_alerts:
            return []
        return group_into_incidents(raw_alerts)
