"""Webhook delivery tasks — reliable outbound HTTP notifications with retry."""

from __future__ import annotations

import logging
from typing import Any

from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="api_gateway.deliver_webhook",
    max_retries=5,
    acks_late=True,
)
def deliver_webhook(self: Any, webhook_url: str, payload: dict[str, Any]) -> None:
    """Deliver a webhook notification to a registered endpoint.

    Retries with exponential back-off on network errors or non-2xx responses.
    """
    import httpx

    backoff = 30 * (2 ** self.request.retries)
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(webhook_url, json=payload)
            if not resp.is_success:
                raise ValueError(
                    f"Webhook endpoint returned {resp.status_code}: {resp.text[:200]}"
                )
        logger.info(
            "webhook_delivered",
            extra={"url": webhook_url, "status": resp.status_code},
        )
    except Exception as exc:
        logger.warning(
            "webhook_delivery_failed",
            extra={
                "url": webhook_url,
                "attempt": self.request.retries + 1,
                "error": str(exc),
            },
        )
        raise self.retry(exc=exc, countdown=backoff)
