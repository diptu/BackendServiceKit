"""Groups the Alerting domain's real `Alert` objects into Incident-shaped
views. A read-only reshaping, not a second incident-tracking datastore —
no state is persisted here. Consumes typed `Alert` objects directly
(in-process), not raw dicts crossing an HTTP boundary.

Alertmanager's `status.state` is one of "active", "suppressed" (silenced),
or "unprocessed". Filtering to `state == "active"` alone correctly
captures "active, non-silenced".
"""

from __future__ import annotations

from typing import Any

from app.domains.alerting.models import Alert
from app.domains.observability.models import Incident


def group_into_incidents(alerts: list[Alert]) -> list[Incident]:
    groups: dict[str, dict[str, Any]] = {}

    for alert in alerts:
        if alert.state != "active":
            continue

        alertname = alert.labels.get("alertname", "unknown")
        service = alert.labels.get("service") or alert.labels.get("job")

        group = groups.setdefault(
            alertname,
            {
                "severity": alert.labels.get("severity"),
                "first_seen": alert.starts_at,
                "services": set(),
                "fingerprints": [],
            },
        )
        if service:
            group["services"].add(service)
        if alert.fingerprint:
            group["fingerprints"].append(alert.fingerprint)
        if alert.starts_at and (
            group["first_seen"] is None or alert.starts_at < group["first_seen"]
        ):
            group["first_seen"] = alert.starts_at

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
