"""RabbitMQ event publisher using aio-pika."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection

from app.core.config import settings

logger = logging.getLogger(__name__)


def _default_serializer(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class RabbitMQPublisher:
    """Fire-and-log publisher: failures are swallowed so the proxy never blocks.

    The connection is shared (created once in lifespan) and injected via
    app.state. Each publish call opens a short-lived channel — aio-pika
    handles channel recycling internally on robust connections.
    """

    def __init__(self, connection: AbstractRobustConnection) -> None:
        self._connection = connection
        self._exchange_name = settings.rabbitmq_exchange

    async def publish(self, routing_key: str, payload: Any) -> None:
        """Publish a JSON-serialised event to the gateway exchange.

        Routing key convention: ``<entity>.<action>``
        e.g. ``gateway.request.completed``, ``cache.tenant.invalidated``
        """
        try:
            async with self._connection.channel() as channel:
                exchange = await channel.declare_exchange(
                    self._exchange_name,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                body = json.dumps(
                    asdict(payload) if hasattr(payload, "__dataclass_fields__") else payload,
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
    """Drop-in for RabbitMQPublisher when RabbitMQ is unavailable."""

    async def publish(self, routing_key: str, payload: Any) -> None:
        logger.debug(
            "event_dropped_no_broker",
            extra={"routing_key": routing_key},
        )
