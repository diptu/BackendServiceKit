"""Reshapes the Alerting domain's real Alert objects into Incidents
(TODO.md Decision #6) — in-process, no HTTP hop."""

from __future__ import annotations

from app.domains.alerting.services.alert_service import AlertService
from app.domains.observability.models import Incident
from app.domains.observability.repositories.incident_repository import group_into_incidents
from app.domains.observability.services.safe_call import safe_call


class IncidentService:
    def __init__(self, alert_service: AlertService) -> None:
        self._alerts = alert_service

    async def list_incidents(self) -> list[Incident]:
        alerts = await safe_call(self._alerts.list_alerts())
        if not alerts:
            return []
        return group_into_incidents(alerts)
