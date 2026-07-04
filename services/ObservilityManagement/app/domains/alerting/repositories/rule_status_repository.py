"""Parses Prometheus's real `GET /api/v1/rules` response into domain objects."""

from __future__ import annotations

from typing import Any

from app.domains.alerting.models import AlertRuleStatus


def parse_rule_statuses(data: dict[str, Any]) -> list[AlertRuleStatus]:
    result: list[AlertRuleStatus] = []
    groups = (data.get("data") or {}).get("groups") or []
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_name = str(group.get("name", ""))
        file_path = str(group.get("file", ""))
        for rule in group.get("rules") or []:
            if not isinstance(rule, dict) or rule.get("type") != "alerting":
                continue
            result.append(
                AlertRuleStatus(
                    name=str(rule.get("name", "")),
                    expr=str(rule.get("query", "")),
                    state=str(rule.get("state", "unknown")),
                    health=str(rule.get("health", "unknown")),
                    group=group_name,
                    file=file_path,
                    duration_seconds=rule.get("duration"),
                    labels=dict(rule.get("labels") or {}),
                    annotations=dict(rule.get("annotations") or {}),
                )
            )
    return result
