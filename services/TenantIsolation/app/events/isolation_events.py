"""Application-level event publishing for isolation domain events."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Protocol

from app.domain.events import (
    IsolationViolationDetected,
    PolicyUpdated,
    ResourceClaimed,
    ResourceClaimReleased,
)

logger = logging.getLogger(__name__)

_ROUTING_KEYS: dict[type, str] = {
    IsolationViolationDetected: "isolation.violation.detected",
    ResourceClaimed: "isolation.claim.registered",
    ResourceClaimReleased: "isolation.claim.released",
    PolicyUpdated: "isolation.policy.updated",
}


class EventPublisher(Protocol):
    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None: ...


async def publish_event(event: object, publisher: EventPublisher) -> None:
    """Serialize a domain event and publish it. Silently drops unknown types."""
    routing_key = _ROUTING_KEYS.get(type(event))
    if routing_key is None:
        logger.warning(
            "unknown_event_type_skipped",
            extra={"event_type": type(event).__name__},
        )
        return

    payload: dict[str, Any] = asdict(event)  # type: ignore[call-overload]
    logger.debug(
        "publishing_domain_event",
        extra={"routing_key": routing_key, "event_type": type(event).__name__},
    )
    try:
        await publisher.publish(routing_key, payload)
    except Exception as exc:
        logger.warning(
            "event_publish_failed",
            extra={"routing_key": routing_key, "error": str(exc)},
        )
