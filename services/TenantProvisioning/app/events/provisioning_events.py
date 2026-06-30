"""Application-level event publishing for provisioning domain events.

Translates domain event dataclasses into RabbitMQ routing keys + JSON payloads
and delegates to the injected publisher. Callers never see RabbitMQ details.

Routing key convention: provisioning.job.<verb>
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Protocol

from app.domain.events import (
    ProvisioningCompleted,
    ProvisioningFailed,
    ProvisioningStarted,
    ProvisioningStepCompleted,
)

logger = logging.getLogger(__name__)

_ROUTING_KEYS: dict[type, str] = {
    ProvisioningStarted: "provisioning.job.started",
    ProvisioningStepCompleted: "provisioning.job.step_completed",
    ProvisioningCompleted: "provisioning.job.completed",
    ProvisioningFailed: "provisioning.job.failed",
}


class EventPublisher(Protocol):
    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None: ...


async def publish_event(event: object, publisher: EventPublisher) -> None:
    """Serialize a domain event dataclass and publish it via the injected publisher.

    Silently drops unknown event types with a warning — never raises.
    """
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
    await publisher.publish(routing_key, payload)
