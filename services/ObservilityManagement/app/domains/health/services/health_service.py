"""Fleet-wide health aggregation for the Health domain.

Composes TargetClient across Tenent + APIGateway, normalizes each one's
`/ready` via ready_shape_repository, and adds a synthetic entry for this
service's own health — no HTTP hop needed for that one since it's the same
process (TODO.md Decision #5).
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.domains.health.infrastructure.target_client import TargetClient
from app.domains.health.infrastructure.target_registry import TargetService, build_target_registry
from app.domains.health.models import DependencyStatus, FleetHealth, ServiceHealth
from app.domains.health.repositories.ready_shape_repository import normalize_ready_body
from app.domains.health.services.uptime_tracker import UptimeTracker


class HealthService:
    def __init__(self, target_client: TargetClient, uptime_tracker: UptimeTracker) -> None:
        self._client = target_client
        self._uptime = uptime_tracker

    async def get_fleet_health(self) -> FleetHealth:
        targets = build_target_registry()
        external = await asyncio.gather(*(self._probe_one(t) for t in targets))
        services = [*external, self._self_health()]
        return FleetHealth(overall_status=_overall_status(services), services=services)

    async def get_service_health(self, name: str) -> ServiceHealth | None:
        if name == settings.app_name:
            return self._self_health()
        target = next((t for t in build_target_registry() if t.name == name), None)
        if target is None:
            return None
        return await self._probe_one(target)

    async def filter_by_dependency(self, *needles: str) -> list[tuple[str, DependencyStatus]]:
        fleet = await self.get_fleet_health()
        lowered_needles = [n.lower() for n in needles]
        matches: list[tuple[str, DependencyStatus]] = []
        for service in fleet.services:
            for dep in service.dependencies:
                dep_name_lower = dep.name.lower()
                if any(needle in dep_name_lower for needle in lowered_needles):
                    matches.append((service.name, dep))
        return matches

    def _self_health(self) -> ServiceHealth:
        uptime = self._uptime.record(settings.app_name, reachable=True)
        raw_health = {"status": "ok", "service": settings.app_name, "version": settings.app_version}
        raw_ready = {"status": "ok"}
        return ServiceHealth(
            name=settings.app_name,
            base_url="http://localhost:8000",
            reachable=True,
            version=settings.app_version,
            observed_uptime_seconds=uptime,
            dependencies=normalize_ready_body(raw_ready),
            raw_health=raw_health,
            raw_ready=raw_ready,
        )

    async def _probe_one(self, target: TargetService) -> ServiceHealth:
        health_result, ready_result = await asyncio.gather(
            self._client.get_health(target.base_url), self._client.get_ready(target.base_url)
        )
        reachable = health_result.reachable
        uptime = self._uptime.record(target.name, reachable=reachable)
        version = health_result.body.get("version") if health_result.body else None

        return ServiceHealth(
            name=target.name,
            base_url=target.base_url,
            reachable=reachable,
            version=str(version) if version is not None else None,
            observed_uptime_seconds=uptime,
            dependencies=normalize_ready_body(ready_result.body),
            raw_health=health_result.body,
            raw_ready=ready_result.body,
        )


def _overall_status(services: list[ServiceHealth]) -> str:
    if not services:
        return "unknown"
    reachable_count = sum(1 for s in services if s.reachable)
    if reachable_count == len(services):
        return "healthy"
    if reachable_count == 0:
        return "unhealthy"
    return "degraded"
