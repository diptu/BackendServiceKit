"""Domain model for the Alerting domain — reshaped from Alertmanager's and
Prometheus's real APIs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Alert:
    fingerprint: str
    labels: dict[str, str]
    annotations: dict[str, str]
    starts_at: str
    ends_at: str
    state: str  # "active" | "suppressed" | "unprocessed"
    silenced_by: list[str] = field(default_factory=list)
    inhibited_by: list[str] = field(default_factory=list)
    receivers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlertRuleStatus:
    """A currently-loaded rule's live view from Prometheus — covers both
    statically-defined and this domain's managed rules. Whether an
    instance is managed depends on `group == settings.managed_rules_group_name`,
    compared by the caller (`AlertingService.is_managed`), not baked in here."""

    name: str
    expr: str
    state: str  # "inactive" | "pending" | "firing"
    health: str
    group: str
    file: str
    duration_seconds: float | None
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AlertRule:
    """A rule this domain can create/update/delete — always lives in the
    managed group."""

    name: str
    expr: str
    for_duration: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
