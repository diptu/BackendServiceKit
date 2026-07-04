"""File-backed store for this domain's exclusively-managed alert rules.

Prometheus has no rule-mutation REST API — rules live in files it loads
at startup/`-reload`. This writes a single YAML file containing one rule
group, atomically (write to a temp file in the same directory, then
`os.replace`) so Prometheus never observes a partially-written file if a
reload races a write.

Synchronous, deliberately — this is a low-frequency admin operation, not a
request-per-second hot path.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from app.domains.alerting.exceptions import RuleAlreadyExistsError, RuleNotFoundError
from app.domains.alerting.models import AlertRule


class RuleFileStore:
    def __init__(self, *, file_path: str, group_name: str) -> None:
        self._path = Path(file_path)
        self._group_name = group_name

    def list_rules(self) -> list[AlertRule]:
        return [_to_rule(r) for r in self._read()]

    def get_rule(self, name: str) -> AlertRule | None:
        for rule in self.list_rules():
            if rule.name == name:
                return rule
        return None

    def create_rule(self, rule: AlertRule) -> None:
        data = self._read()
        if any(r.get("alert") == rule.name for r in data):
            raise RuleAlreadyExistsError(f"Rule {rule.name!r} already exists.")
        data.append(_from_rule(rule))
        self._write(data)

    def update_rule(self, name: str, rule: AlertRule) -> None:
        data = self._read()
        idx = next((i for i, r in enumerate(data) if r.get("alert") == name), None)
        if idx is None:
            raise RuleNotFoundError(f"Managed rule {name!r} not found.")
        data[idx] = _from_rule(rule)
        self._write(data)

    def delete_rule(self, name: str) -> None:
        data = self._read()
        new_data = [r for r in data if r.get("alert") != name]
        if len(new_data) == len(data):
            raise RuleNotFoundError(f"Managed rule {name!r} not found.")
        self._write(new_data)

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        for group in doc.get("groups", []) or []:
            if group.get("name") == self._group_name:
                rules = group.get("rules", [])
                return list(rules) if isinstance(rules, list) else []
        return []

    def _write(self, rules: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"groups": [{"name": self._group_name, "rules": rules}]}
        fd, tmp_path = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump(doc, f, sort_keys=False)
            os.replace(tmp_path, self._path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


def _to_rule(raw: dict[str, Any]) -> AlertRule:
    return AlertRule(
        name=str(raw.get("alert", "")),
        expr=str(raw.get("expr", "")),
        for_duration=raw.get("for"),
        labels=dict(raw.get("labels", {}) or {}),
        annotations=dict(raw.get("annotations", {}) or {}),
    )


def _from_rule(rule: AlertRule) -> dict[str, Any]:
    raw: dict[str, Any] = {"alert": rule.name, "expr": rule.expr}
    if rule.for_duration:
        raw["for"] = rule.for_duration
    if rule.labels:
        raw["labels"] = dict(rule.labels)
    if rule.annotations:
        raw["annotations"] = dict(rule.annotations)
    return raw
