from __future__ import annotations

from app.repositories.incident_repository import group_into_incidents


def test_empty_alerts_yields_no_incidents() -> None:
    assert group_into_incidents([]) == []


def test_suppressed_alerts_are_excluded() -> None:
    alerts = [
        {
            "fingerprint": "a1",
            "state": "suppressed",
            "labels": {"alertname": "ServiceDown", "service": "tenent"},
            "starts_at": "2024-01-01T00:00:00Z",
        }
    ]
    assert group_into_incidents(alerts) == []


def test_active_alert_becomes_one_incident() -> None:
    alerts = [
        {
            "fingerprint": "a1",
            "state": "active",
            "labels": {"alertname": "ServiceDown", "service": "tenent", "severity": "critical"},
            "starts_at": "2024-01-01T00:00:00Z",
        }
    ]
    incidents = group_into_incidents(alerts)
    assert len(incidents) == 1
    assert incidents[0].alertname == "ServiceDown"
    assert incidents[0].severity == "critical"
    assert incidents[0].affected_services == ["tenent"]
    assert incidents[0].fingerprints == ["a1"]


def test_same_alertname_across_services_groups_into_one_incident() -> None:
    alerts = [
        {
            "fingerprint": "a1",
            "state": "active",
            "labels": {"alertname": "ServiceDown", "service": "tenent"},
            "starts_at": "2024-01-01T00:00:10Z",
        },
        {
            "fingerprint": "a2",
            "state": "active",
            "labels": {"alertname": "ServiceDown", "service": "alerting"},
            "starts_at": "2024-01-01T00:00:00Z",
        },
    ]
    incidents = group_into_incidents(alerts)
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.affected_services == ["alerting", "tenent"]
    assert set(incident.fingerprints) == {"a1", "a2"}
    # earliest starts_at wins
    assert incident.first_seen == "2024-01-01T00:00:00Z"


def test_different_alertnames_produce_separate_incidents() -> None:
    alerts = [
        {
            "fingerprint": "a1",
            "state": "active",
            "labels": {"alertname": "ServiceDown", "service": "tenent"},
            "starts_at": "2024-01-01T00:00:00Z",
        },
        {
            "fingerprint": "a2",
            "state": "active",
            "labels": {"alertname": "HighLatency", "service": "tenent"},
            "starts_at": "2024-01-01T00:00:00Z",
        },
    ]
    incidents = group_into_incidents(alerts)
    assert {i.alertname for i in incidents} == {"ServiceDown", "HighLatency"}


def test_job_label_used_when_service_label_absent() -> None:
    alerts = [
        {
            "fingerprint": "a1",
            "state": "active",
            "labels": {"alertname": "PrometheusTargetDown", "job": "kong"},
            "starts_at": "2024-01-01T00:00:00Z",
        }
    ]
    incidents = group_into_incidents(alerts)
    assert incidents[0].affected_services == ["kong"]


def test_malformed_alert_entries_are_ignored_safely() -> None:
    alerts = ["not-a-dict", None, 42]
    assert group_into_incidents(alerts) == []  # type: ignore[arg-type]
