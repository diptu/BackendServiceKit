"""RabbitMQ event publisher — fire-and-log, never blocks the caller."""

from __future__ import annotations

import json
import logging
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self, connection: aio_pika.abc.AbstractRobustConnection) -> None:
        self._connection = connection

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        try:
            channel = await self._connection.channel()
            exchange = await channel.declare_exchange(
                settings.rabbitmq_exchange,
                ExchangeType.TOPIC,
                durable=True,
            )
            await exchange.publish(
                Message(
                    body=json.dumps(payload, default=str).encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                ),
                routing_key=routing_key,
            )
        except Exception as exc:
            logger.warning(
                "rabbitmq_publish_failed",
                extra={"routing_key": routing_key, "error": str(exc)},
            )


class NullPublisher:
    """Drop-in when RabbitMQ is unavailable (tests / degraded mode)."""

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        logger.debug(
            "null_publisher_skipped",
            extra={"routing_key": routing_key},
        )
