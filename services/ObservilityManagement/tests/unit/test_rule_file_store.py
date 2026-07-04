from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.alerting.exceptions import RuleAlreadyExistsError, RuleNotFoundError
from app.domains.alerting.infrastructure.rule_file_store import RuleFileStore
from app.domains.alerting.models import AlertRule


@pytest.fixture
def store(tmp_path: Path) -> RuleFileStore:
    return RuleFileStore(
        file_path=str(tmp_path / "nested" / "managed.yml"), group_name="test-group"
    )


def test_list_rules_empty_when_file_does_not_exist(store: RuleFileStore) -> None:
    assert store.list_rules() == []


def test_create_then_list_round_trips(store: RuleFileStore) -> None:
    rule = AlertRule(name="HighMemory", expr="process_memory > 100", for_duration="5m")
    store.create_rule(rule)
    rules = store.list_rules()
    assert len(rules) == 1
    assert rules[0] == rule


def test_create_duplicate_name_raises(store: RuleFileStore) -> None:
    rule = AlertRule(name="Dup", expr="up == 0")
    store.create_rule(rule)
    with pytest.raises(RuleAlreadyExistsError):
        store.create_rule(rule)


def test_update_rule_replaces_existing(store: RuleFileStore) -> None:
    store.create_rule(AlertRule(name="R1", expr="up == 0"))
    store.update_rule("R1", AlertRule(name="R1", expr="up == 1"))
    rule = store.get_rule("R1")
    assert rule is not None
    assert rule.expr == "up == 1"


def test_update_missing_rule_raises(store: RuleFileStore) -> None:
    with pytest.raises(RuleNotFoundError):
        store.update_rule("Ghost", AlertRule(name="Ghost", expr="up == 0"))


def test_delete_rule_removes_it(store: RuleFileStore) -> None:
    store.create_rule(AlertRule(name="ToDelete", expr="up == 0"))
    store.delete_rule("ToDelete")
    assert store.get_rule("ToDelete") is None


def test_delete_missing_rule_raises(store: RuleFileStore) -> None:
    with pytest.raises(RuleNotFoundError):
        store.delete_rule("Ghost")
