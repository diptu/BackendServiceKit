"""Alert rule read/CRUD business logic.

`list_rule_statuses` shows every loaded rule (static + managed) via
Prometheus's own live `GET /api/v1/rules`. `create_rule`/`update_rule`/
`delete_rule` only ever touch this domain's exclusively-managed file —
attempting to mutate a rule that lives in a static file raises
`RuleNotManagedError` rather than silently doing nothing.
"""

from __future__ import annotations

from app.domains.alerting.exceptions import (
    PrometheusError,
    PrometheusUnavailableError,
    RuleNotFoundError,
    RuleNotManagedError,
)
from app.domains.alerting.infrastructure.prometheus_rules_client import PrometheusRulesClient
from app.domains.alerting.infrastructure.rule_file_store import RuleFileStore
from app.domains.alerting.models import AlertRule, AlertRuleStatus
from app.domains.alerting.repositories.rule_status_repository import parse_rule_statuses


class RuleService:
    def __init__(
        self,
        rule_store: RuleFileStore,
        prometheus_client: PrometheusRulesClient,
        *,
        managed_group_name: str,
    ) -> None:
        self._store = rule_store
        self._prom = prometheus_client
        self._managed_group_name = managed_group_name

    async def list_rule_statuses(self) -> list[AlertRuleStatus]:
        data = await self._prom.list_rules()
        return parse_rule_statuses(data)

    async def get_rule_status(self, name: str) -> AlertRuleStatus | None:
        for status in await self.list_rule_statuses():
            if status.name == name:
                return status
        return None

    def is_managed(self, status: AlertRuleStatus) -> bool:
        return status.group == self._managed_group_name

    async def create_rule(self, rule: AlertRule) -> None:
        self._store.create_rule(rule)
        await self._prom.reload()

    async def update_rule(self, name: str, rule: AlertRule) -> None:
        if self._store.get_rule(name) is None:
            await self._raise_if_defined_elsewhere(name)
            raise RuleNotFoundError(f"Managed rule {name!r} not found.")
        self._store.update_rule(name, rule)
        await self._prom.reload()

    async def delete_rule(self, name: str) -> None:
        if self._store.get_rule(name) is None:
            await self._raise_if_defined_elsewhere(name)
            raise RuleNotFoundError(f"Managed rule {name!r} not found.")
        self._store.delete_rule(name)
        await self._prom.reload()

    async def _raise_if_defined_elsewhere(self, name: str) -> None:
        try:
            statuses = await self.list_rule_statuses()
        except (PrometheusUnavailableError, PrometheusError):
            return
        for status in statuses:
            if status.name == name and not self.is_managed(status):
                raise RuleNotManagedError(name)
