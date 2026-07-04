"""Alert query/action business logic — composes AlertmanagerClient +
alert_repository. Acknowledge creates a real Alertmanager silence; resolve
is real for externally-pushed alerts, best-effort for Prometheus-sourced
ones (Alertmanager's alert state is derived from whatever the source keeps
sending, so a still-firing Prometheus alert will be re-sent on its next
evaluation cycle regardless of a manual resolve here)."""

from __future__ import annotations

from app.domains.alerting.exceptions import AlertNotFoundError
from app.domains.alerting.infrastructure.alertmanager_client import AlertmanagerClient
from app.domains.alerting.models import Alert
from app.domains.alerting.repositories.alert_repository import (
    build_push_payload,
    build_resolve_payload,
    build_silence_payload,
    parse_alerts,
)

_TEST_ALERT_NAME = "AlertingDomainTestAlert"


class AlertService:
    def __init__(
        self, alertmanager_client: AlertmanagerClient, *, default_ack_minutes: float
    ) -> None:
        self._am = alertmanager_client
        self._default_ack_minutes = default_ack_minutes

    async def list_alerts(self) -> list[Alert]:
        """Lets AlertmanagerUnavailableError/AlertmanagerError propagate —
        this domain's own router turns those into proper 503/502
        responses. Cross-domain callers (Monitoring, Observability) are
        responsible for catching these themselves (see TODO.md Decision
        #4's "wrap every cross-domain call" rule) rather than this method
        silently degrading to None, since that would hide a real error
        from its own API consumers."""
        raw = await self._am.list_alerts()
        return parse_alerts(raw)

    async def get_alert(self, fingerprint: str) -> Alert:
        alerts = await self.list_alerts()
        for alert in alerts:
            if alert.fingerprint == fingerprint:
                return alert
        raise AlertNotFoundError(f"No alert with fingerprint {fingerprint!r}.")

    async def push_alert(
        self,
        *,
        labels: dict[str, str],
        annotations: dict[str, str],
        generator_url: str | None = None,
        ends_in_minutes: float | None = None,
    ) -> None:
        payload = build_push_payload(
            labels=labels,
            annotations=annotations,
            generator_url=generator_url,
            ends_in_minutes=ends_in_minutes,
        )
        await self._am.post_alerts([payload])

    async def acknowledge(
        self,
        fingerprint: str,
        *,
        duration_minutes: float | None = None,
        comment: str = "",
        created_by: str = "observability-management",
    ) -> str:
        alert = await self.get_alert(fingerprint)
        payload = build_silence_payload(
            alert,
            duration_minutes=duration_minutes or self._default_ack_minutes,
            created_by=created_by,
            comment=comment or "Acknowledged via ObservilityManagement",
        )
        return await self._am.create_silence(silence=payload)

    async def resolve(self, fingerprint: str) -> None:
        alert = await self.get_alert(fingerprint)
        payload = build_resolve_payload(alert)
        await self._am.post_alerts([payload])

    async def send_test_alert(self) -> dict[str, dict[str, str]]:
        labels = {"alertname": _TEST_ALERT_NAME, "severity": "info", "service": "alerting"}
        annotations = {
            "summary": "Synthetic test alert from ObservilityManagement's Alerting domain",
            "description": (
                "Verifies the Alertmanager routing/notification pipeline end to "
                "end. Auto-expires shortly and requires no action."
            ),
        }
        await self.push_alert(labels=labels, annotations=annotations, ends_in_minutes=1)
        return {"labels": labels, "annotations": annotations}
