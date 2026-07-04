"""Request/response schemas for the Alerting domain."""

from __future__ import annotations

from pydantic import Field

from app.core.schema_base import APIModel
from app.domains.alerting.models import Alert, AlertRule, AlertRuleStatus


class AlertResponse(APIModel):
    fingerprint: str
    labels: dict[str, str]
    annotations: dict[str, str]
    starts_at: str
    ends_at: str
    state: str
    silenced_by: list[str] = Field(default_factory=list)
    inhibited_by: list[str] = Field(default_factory=list)
    receivers: list[str] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, alert: Alert) -> "AlertResponse":
        return cls(
            fingerprint=alert.fingerprint,
            labels=alert.labels,
            annotations=alert.annotations,
            starts_at=alert.starts_at,
            ends_at=alert.ends_at,
            state=alert.state,
            silenced_by=alert.silenced_by,
            inhibited_by=alert.inhibited_by,
            receivers=alert.receivers,
        )


class AlertListResponse(APIModel):
    items: list[AlertResponse]
    count: int


class AlertPushCreate(APIModel):
    labels: dict[str, str]
    annotations: dict[str, str] = Field(default_factory=dict)
    generator_url: str | None = None
    ends_in_minutes: float | None = None


class PushAcceptedResponse(APIModel):
    accepted: bool


class AcknowledgeRequest(APIModel):
    duration_minutes: float | None = None
    comment: str = ""
    created_by: str = "observability-management"


class AcknowledgeResponse(APIModel):
    silence_id: str


class ResolveResponse(APIModel):
    resolved: bool


class TestAlertResponse(APIModel):
    labels: dict[str, str]
    annotations: dict[str, str]


class AlertRuleStatusResponse(APIModel):
    name: str
    expr: str
    state: str
    health: str
    group: str
    file: str
    duration_seconds: float | None
    managed: bool
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, status: AlertRuleStatus, *, managed: bool) -> "AlertRuleStatusResponse":
        return cls(
            name=status.name,
            expr=status.expr,
            state=status.state,
            health=status.health,
            group=status.group,
            file=status.file,
            duration_seconds=status.duration_seconds,
            managed=managed,
            labels=status.labels,
            annotations=status.annotations,
        )


class AlertRuleStatusListResponse(APIModel):
    items: list[AlertRuleStatusResponse]
    count: int


class AlertRuleCreate(APIModel):
    name: str
    expr: str
    for_duration: str | None = Field(default=None, alias="for")
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    def to_domain(self) -> AlertRule:
        return AlertRule(
            name=self.name,
            expr=self.expr,
            for_duration=self.for_duration,
            labels=self.labels,
            annotations=self.annotations,
        )


class RuleMutationResponse(APIModel):
    name: str
    reloaded: bool
