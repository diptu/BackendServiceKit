"""Parses Alertmanager's real v2 API responses into domain objects, and
builds the payloads it expects for pushing alerts / creating silences."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.domains.alerting.models import Alert

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


def _iso_now() -> str:
    return datetime.now(UTC).strftime(_ISO_FORMAT)


def _iso_in(minutes: float) -> str:
    dt = datetime.now(UTC) + timedelta(minutes=minutes)
    return dt.strftime(_ISO_FORMAT)


def parse_alert(raw: dict[str, Any]) -> Alert:
    status = raw.get("status") or {}
    receivers = [r.get("name", "") for r in (raw.get("receivers") or []) if isinstance(r, dict)]
    return Alert(
        fingerprint=str(raw.get("fingerprint", "")),
        labels=dict(raw.get("labels") or {}),
        annotations=dict(raw.get("annotations") or {}),
        starts_at=str(raw.get("startsAt", "")),
        ends_at=str(raw.get("endsAt", "")),
        state=str(status.get("state", "unprocessed")),
        silenced_by=list(status.get("silencedBy") or []),
        inhibited_by=list(status.get("inhibitedBy") or []),
        receivers=receivers,
    )


def parse_alerts(raw_list: list[dict[str, Any]]) -> list[Alert]:
    return [parse_alert(r) for r in raw_list]


def build_push_payload(
    *,
    labels: dict[str, str],
    annotations: dict[str, str],
    generator_url: str | None = None,
    ends_in_minutes: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"labels": labels, "annotations": annotations, "startsAt": _iso_now()}
    if generator_url:
        payload["generatorURL"] = generator_url
    if ends_in_minutes is not None:
        payload["endsAt"] = _iso_in(ends_in_minutes)
    return payload


def build_resolve_payload(alert: Alert) -> dict[str, Any]:
    return {
        "labels": alert.labels,
        "annotations": alert.annotations,
        "startsAt": alert.starts_at,
        "endsAt": _iso_now(),
    }


def build_silence_payload(
    alert: Alert, *, duration_minutes: float, created_by: str, comment: str
) -> dict[str, Any]:
    matchers = [{"name": k, "value": v, "isRegex": False} for k, v in alert.labels.items()]
    return {
        "matchers": matchers,
        "startsAt": _iso_now(),
        "endsAt": _iso_in(duration_minutes),
        "createdBy": created_by,
        "comment": comment,
    }
