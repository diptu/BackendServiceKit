"""Tests the Observability domain's incident grouping now that it consumes
real, typed Alert objects directly (in-process)."""

from __future__ import annotations

from app.domains.alerting.models import Alert
from app.domains.observability.repositories.incident_repository import group_into_incidents


def _alert(**overrides: object) -> Alert:
    defaults: dict[str, object] = {
        "fingerprint": "a1",
        "labels": {"alertname": "ServiceDown", "service": "tenent"},
        "annotations": {},
        "starts_at": "2024-01-01T00:00:00Z",
        "ends_at": "",
        "state": "active",
    }
    defaults.update(overrides)
    return Alert(**defaults)  # type: ignore[arg-type]


def test_empty_alerts_yields_no_incidents() -> None:
    assert group_into_incidents([]) == []


def test_suppressed_alerts_are_excluded() -> None:
    assert group_into_incidents([_alert(state="suppressed")]) == []


def test_active_alert_becomes_one_incident() -> None:
    incidents = group_into_incidents(
        [_alert(labels={"alertname": "X", "service": "tenent", "severity": "critical"})]
    )
    assert len(incidents) == 1
    assert incidents[0].alertname == "X"
    assert incidents[0].severity == "critical"
    assert incidents[0].affected_services == ["tenent"]


def test_same_alertname_across_services_groups_into_one_incident() -> None:
    alerts = [
        _alert(
            fingerprint="a1",
            labels={"alertname": "X", "service": "tenent"},
            starts_at="2024-01-01T00:00:10Z",
        ),
        _alert(
            fingerprint="a2",
            labels={"alertname": "X", "service": "alerting"},
            starts_at="2024-01-01T00:00:00Z",
        ),
    ]
    incidents = group_into_incidents(alerts)
    assert len(incidents) == 1
    assert incidents[0].affected_services == ["alerting", "tenent"]
    assert incidents[0].first_seen == "2024-01-01T00:00:00Z"
