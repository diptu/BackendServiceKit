"""Audit logging tasks — ship request/response records asynchronously."""

from __future__ import annotations

import logging
from typing import Any

from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="api_gateway.audit_request",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def audit_request(self: Any, event_data: dict[str, Any]) -> None:
    """Persist a gateway request audit record.

    In production this would forward to the AuditLogging service via HTTP
    or publish to a dedicated audit exchange. Currently writes a structured
    log entry as the baseline implementation.
    """
    try:
        logger.info(
            "audit_record",
            extra={
                "request_id": event_data.get("request_id"),
                "method": event_data.get("method"),
                "path": event_data.get("path"),
                "upstream": event_data.get("upstream"),
                "status_code": event_data.get("status_code"),
                "tenant_id": event_data.get("tenant_id"),
            },
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
