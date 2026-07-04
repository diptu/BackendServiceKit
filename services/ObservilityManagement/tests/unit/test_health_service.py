"""Tests the Health domain's shrunk registry (Tenent + APIGateway + self)
— TODO.md Decision #5."""

from __future__ import annotations

from app.core.config import settings
from app.domains.health.infrastructure.target_client import TargetProbeResult
from app.domains.health.services.health_service import HealthService
from app.domains.health.services.uptime_tracker import UptimeTracker


class _FakeTargetClient:
    def __init__(self, responses: dict[str, tuple[TargetProbeResult, TargetProbeResult]]) -> None:
        self._responses = responses

    async def get_health(self, base_url: str) -> TargetProbeResult:
        return self._responses[base_url][0]

    async def get_ready(self, base_url: str) -> TargetProbeResult:
        return self._responses[base_url][1]


def _ok(body: dict) -> TargetProbeResult:
    return TargetProbeResult(body=body, status_code=200, latency_ms=1.0, error=None)


def _down() -> TargetProbeResult:
    return TargetProbeResult(body=None, status_code=None, latency_ms=None, error="connect failed")


async def test_fleet_health_includes_self_entry_always_reachable() -> None:
    from app.domains.health.infrastructure.target_registry import build_target_registry

    targets = build_target_registry()
    responses = {t.base_url: (_down(), _down()) for t in targets}
    service = HealthService(_FakeTargetClient(responses), UptimeTracker())  # type: ignore[arg-type]
    fleet = await service.get_fleet_health()

    self_entry = next(s for s in fleet.services if s.name == settings.app_name)
    assert self_entry.reachable is True
    assert self_entry.version == settings.app_version
    # registry shrank to 2 external targets + self = 3 total
    assert len(fleet.services) == 3


async def test_one_dead_external_target_marks_only_itself_unreachable() -> None:
    from app.domains.health.infrastructure.target_registry import build_target_registry

    targets = build_target_registry()
    responses = {}
    for i, t in enumerate(targets):
        responses[t.base_url] = (
            (_down(), _down()) if i == 0 else (_ok({"status": "ok"}), _ok({"status": "ok"}))
        )
    service = HealthService(_FakeTargetClient(responses), UptimeTracker())  # type: ignore[arg-type]
    fleet = await service.get_fleet_health()

    external_unreachable = [s for s in fleet.services if not s.reachable]
    assert len(external_unreachable) == 1
    assert fleet.overall_status == "degraded"


async def test_get_service_health_for_self() -> None:
    service = HealthService(_FakeTargetClient({}), UptimeTracker())  # type: ignore[arg-type]
    result = await service.get_service_health(settings.app_name)
    assert result is not None
    assert result.reachable is True


async def test_get_service_health_unknown_returns_none() -> None:
    service = HealthService(_FakeTargetClient({}), UptimeTracker())  # type: ignore[arg-type]
    assert await service.get_service_health("does-not-exist") is None
