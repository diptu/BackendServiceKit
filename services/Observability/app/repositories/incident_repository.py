"""Groups Alerting's raw active-alert items into Incident-shaped views —
see TODO.md Decision #6. A read-only reshaping, not a second
incident-tracking datastore — no state is persisted here.

Alertmanager's `status.state` is one of "active", "suppressed" (silenced),
or "unprocessed". Filtering to `state == "active"` alone correctly captures
"active, non-silenced" — a silenced alert reports `state == "suppressed"`,
never `"active"` (verified against a real Alertmanager while building
`services/Alerting/`).
"""

from __future__ import annotations

from typing import Any

from app.domain.observability import Incident


def group_into_incidents(raw_alerts: list[dict[str, Any]]) -> list[Incident]:
    groups: dict[str, dict[str, Any]] = {}

    for alert in raw_alerts:
        if not isinstance(alert, dict) or alert.get("state") != "active":
            continue

        labels = alert.get("labels") or {}
        alertname = str(labels.get("alertname", "unknown"))
        service = labels.get("service") or labels.get("job")
        starts_at = alert.get("starts_at")
        fingerprint = alert.get("fingerprint")

        group = groups.setdefault(
            alertname,
            {
                "severity": labels.get("severity"),
                "first_seen": starts_at,
                "services": set(),
                "fingerprints": [],
            },
        )
        if service:
            group["services"].add(str(service))
        if fingerprint:
            group["fingerprints"].append(str(fingerprint))
        if starts_at and (group["first_seen"] is None or starts_at < group["first_seen"]):
            group["first_seen"] = starts_at

    return [
        Incident(
            alertname=name,
            severity=data["severity"],
            first_seen=data["first_seen"],
            affected_services=sorted(data["services"]),
            fingerprints=data["fingerprints"],
        )
        for name, data in groups.items()
    ]
