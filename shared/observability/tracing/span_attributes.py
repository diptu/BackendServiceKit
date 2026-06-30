"""Helpers for stamping active spans with NutraTenant domain attributes."""

from __future__ import annotations

from opentelemetry.trace import Span

from shared.observability.constants.attributes import ISOLATION_DECISION, LIFECYCLE_STATE, REQUEST_ID, TENANT_ID


def set_tenant_span_attributes(
    span: Span,
    *,
    tenant_id: str | None = None,
    request_id: str | None = None,
    lifecycle_state: str | None = None,
    isolation_decision: str | None = None,
) -> None:
    """Stamp the given span with NutraTenant-specific attributes."""
    if tenant_id:
        span.set_attribute(TENANT_ID, tenant_id)
    if request_id:
        span.set_attribute(REQUEST_ID, request_id)
    if lifecycle_state:
        span.set_attribute(LIFECYCLE_STATE, lifecycle_state)
    if isolation_decision:
        span.set_attribute(ISOLATION_DECISION, isolation_decision)
