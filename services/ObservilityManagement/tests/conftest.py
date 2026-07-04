"""Shared test fixtures for ObservilityManagement."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Annotated

import httpx
import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.domains.alerting.dependencies import get_prometheus_rules_client
from app.domains.alerting.infrastructure.prometheus_rules_client import PrometheusRulesClient
from app.domains.alerting.infrastructure.rule_file_store import RuleFileStore
from app.domains.alerting.services.rule_service import RuleService
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_rule_store(tmp_path: Path) -> Iterator[None]:
    """Route Alerting rule CRUD in tests at a throwaway file, never the
    real MANAGED_RULES_FILE_PATH — RuleFileStore does real file I/O."""
    from app.domains.alerting.dependencies import get_rule_service

    store = RuleFileStore(
        file_path=str(tmp_path / "managed.yml"), group_name=settings.managed_rules_group_name
    )

    def _override(
        prom_client: Annotated[PrometheusRulesClient, Depends(get_prometheus_rules_client)],
    ) -> RuleService:
        return RuleService(store, prom_client, managed_group_name=settings.managed_rules_group_name)

    app.dependency_overrides[get_rule_service] = _override
    yield
    app.dependency_overrides.pop(get_rule_service, None)


@pytest.fixture(autouse=True)
def _clear_uptime_tracker() -> Iterator[None]:
    from app.domains.health import dependencies as health_dependencies

    health_dependencies._uptime_tracker.clear()
    yield
    health_dependencies._uptime_tracker.clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.state.http_client = httpx.AsyncClient(timeout=5.0)
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await app.state.http_client.aclose()
