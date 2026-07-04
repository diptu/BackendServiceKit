from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.domains.alerting.exceptions import (
    PrometheusUnavailableError,
    RuleNotFoundError,
    RuleNotManagedError,
)
from app.domains.alerting.infrastructure.rule_file_store import RuleFileStore
from app.domains.alerting.models import AlertRule
from app.domains.alerting.services.rule_service import RuleService

_MANAGED_GROUP = "alerting-service-managed"


class _FakePrometheusRulesClient:
    def __init__(
        self, response: dict[str, Any] | None = None, *, unavailable: bool = False
    ) -> None:
        self._response = response or {"data": {"groups": []}}
        self._unavailable = unavailable
        self.reload_called = False

    async def list_rules(self) -> dict[str, Any]:
        if self._unavailable:
            raise PrometheusUnavailableError("down")
        return self._response

    async def reload(self) -> None:
        self.reload_called = True


def _rules_response(*, static_names: list[str], managed_names: list[str]) -> dict[str, Any]:
    def _group(name: str, rule_names: list[str]) -> dict[str, Any]:
        return {
            "name": name,
            "file": f"/etc/prometheus/alerts/{name}.yml",
            "rules": [
                {
                    "type": "alerting",
                    "name": rn,
                    "query": "up == 0",
                    "state": "inactive",
                    "health": "ok",
                    "duration": 60,
                    "labels": {},
                    "annotations": {},
                }
                for rn in rule_names
            ],
        }

    groups = []
    if static_names:
        groups.append(_group("nutratenant.static", static_names))
    if managed_names:
        groups.append(_group(_MANAGED_GROUP, managed_names))
    return {"data": {"groups": groups}}


@pytest.fixture
def store(tmp_path: Path) -> RuleFileStore:
    return RuleFileStore(file_path=str(tmp_path / "managed.yml"), group_name=_MANAGED_GROUP)


def _make_service(store: RuleFileStore, prom: _FakePrometheusRulesClient) -> RuleService:
    return RuleService(store, prom, managed_group_name=_MANAGED_GROUP)  # type: ignore[arg-type]


async def test_create_rule_writes_file_and_reloads_prometheus(store: RuleFileStore) -> None:
    prom = _FakePrometheusRulesClient()
    service = _make_service(store, prom)
    await service.create_rule(AlertRule(name="NewRule", expr="up == 0"))
    assert store.get_rule("NewRule") is not None
    assert prom.reload_called is True


async def test_update_rule_defined_in_static_file_raises_not_managed(store: RuleFileStore) -> None:
    prom = _FakePrometheusRulesClient(
        _rules_response(static_names=["ServiceDown"], managed_names=[])
    )
    service = _make_service(store, prom)
    with pytest.raises(RuleNotManagedError):
        await service.update_rule("ServiceDown", AlertRule(name="ServiceDown", expr="up == 0"))


async def test_update_truly_missing_rule_raises_not_found(store: RuleFileStore) -> None:
    prom = _FakePrometheusRulesClient(_rules_response(static_names=[], managed_names=[]))
    service = _make_service(store, prom)
    with pytest.raises(RuleNotFoundError):
        await service.update_rule("Ghost", AlertRule(name="Ghost", expr="up == 0"))


async def test_update_degrades_to_not_found_when_prometheus_unreachable(
    store: RuleFileStore,
) -> None:
    prom = _FakePrometheusRulesClient(unavailable=True)
    service = _make_service(store, prom)
    with pytest.raises(RuleNotFoundError):
        await service.update_rule("Ghost", AlertRule(name="Ghost", expr="up == 0"))


async def test_delete_managed_rule_succeeds_and_reloads(store: RuleFileStore) -> None:
    prom = _FakePrometheusRulesClient()
    service = _make_service(store, prom)
    await service.create_rule(AlertRule(name="ToDelete", expr="up == 0"))
    prom.reload_called = False
    await service.delete_rule("ToDelete")
    assert store.get_rule("ToDelete") is None
    assert prom.reload_called is True
