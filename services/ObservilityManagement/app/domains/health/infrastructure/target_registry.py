"""Static registry of external HTTP targets this domain normalizes health
for — Tenent and APIGateway only. This service's own health is a synthetic
entry `HealthService` constructs directly (no HTTP hop needed since it's
the same process) — see TODO.md Decision #5: the fleet shrank from eight
targets (before the seven-service merge) to these two plus self.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class TargetService:
    name: str
    base_url: str


def build_target_registry() -> list[TargetService]:
    return [
        TargetService(name="tenent", base_url=settings.tenent_base_url),
        TargetService(name="api-gateway", base_url=settings.api_gateway_base_url),
    ]
