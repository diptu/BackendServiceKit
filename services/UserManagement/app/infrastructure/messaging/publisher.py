"""RabbitMQ event publisher using aio-pika.

Copied from services/APIGateway/app/infrastructure/messaging/publisher.py —
the only place in this repo where this pattern is genuinely wired up and
tested (connection created once in main.py's lifespan, shared via
app.state, injected per-request). Tenent also defines a
RabbitMQPublisher/NullPublisher pair, but it's dead code: never
instantiated or referenced anywhere outside its own file — Tenent's real
cross-service notification uses a direct HTTP client instead. Copy
APIGateway's proven shape, not Tenent's unwired one.

One bug found and fixed while verifying this against real RabbitMQ:
`_default_serializer` only handled `datetime`, not `UUID` — every event
dataclass in this service carries raw UUID fields (user_id, tenant_id,
...), so `json.dumps` failed with "Object of type UUID is not JSON
serializable" on the very first publish. This is a latent bug in
APIGateway's own publisher.py too (untested there because its own event
payloads apparently never carry a raw UUID field directly) — fixed here,
not backported there (out of scope for this service's build).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection

from app.core.config import settings

logger = logging.getLogger(__name__)


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class RabbitMQPublisher:
    """Fire-and-log publisher: failures are swallowed so callers never block.

    The connection is shared (created once in lifespan) and injected via
    app.state. Each publish call opens a short-lived channel — aio-pika
    handles channel recycling internally on robust connections.
    """

    def __init__(self, connection: AbstractRobustConnection) -> None:
        self._connection = connection
        self._exchange_name = settings.rabbitmq_exchange

    async def publish(self, routing_key: str, payload: Any) -> None:
        """Publish a JSON-serialised event to the identity.events exchange.

        Routing key convention: ``<entity>.<action>``, e.g. ``user.created``.
        """
        try:
            async with self._connection.channel() as channel:
                exchange = await channel.declare_exchange(
                    self._exchange_name,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                body = json.dumps(
                    asdict(payload)
                    if hasattr(payload, "__dataclass_fields__")
                    else payload,
                    default=_default_serializer,
                ).encode()
                message = aio_pika.Message(
                    body=body,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                )
                await exchange.publish(message, routing_key=routing_key)
                logger.debug(
                    "event_published",
                    extra={"routing_key": routing_key, "bytes": len(body)},
                )
        except Exception as exc:
            logger.warning(
                "rabbitmq_publish_failed",
                extra={"routing_key": routing_key, "error": str(exc)},
            )


class NullPublisher:
    """Drop-in for RabbitMQPublisher when RabbitMQ is unavailable (tests / degraded mode)."""

    async def publish(self, routing_key: str, payload: Any) -> None:
        logger.debug("event_dropped_no_broker", extra={"routing_key": routing_key})
