"""RabbitMQ event consumer — listens for tenant.created and tenant.status.changed events.

When a tenant.created event arrives (from TenantManagement) or a status.changed event
with to_status=provisioning arrives (from TenantLifecycle), this consumer triggers
the provisioning workflow automatically.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

import aio_pika

logger = logging.getLogger(__name__)

_StartProvisioningFn = Callable[[UUID], Coroutine[Any, Any, None]]

_TENANT_EVENTS_EXCHANGE = "tenant.events"
_QUEUE_NAME = "tenant-provisioning.tenant-events"


class TenantEventConsumer:
    def __init__(
        self,
        connection: aio_pika.abc.AbstractRobustConnection,
        start_provisioning: _StartProvisioningFn,
    ) -> None:
        self._connection = connection
        self._start_provisioning = start_provisioning
        self._consumer_tag: str | None = None
        self._queue: aio_pika.abc.AbstractRobustQueue | None = None

    async def start(self) -> None:
        channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            _TENANT_EVENTS_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        self._queue = await channel.declare_queue(_QUEUE_NAME, durable=True)
        await self._queue.bind(exchange, routing_key="tenant.created")
        await self._queue.bind(exchange, routing_key="tenant.status.changed")

        self._consumer_tag = (
            await self._queue.consume(self._handle_message)
        ).consumer_tag
        logger.info("tenant_event_consumer_started", extra={"queue": _QUEUE_NAME})

    async def stop(self) -> None:
        if self._queue and self._consumer_tag:
            await self._queue.cancel(self._consumer_tag)
        logger.info("tenant_event_consumer_stopped")

    async def _handle_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                payload: dict[str, Any] = json.loads(message.body)
                routing_key = message.routing_key or ""
                tenant_id_raw = payload.get("tenant_id") or payload.get("id")

                if not tenant_id_raw:
                    logger.warning(
                        "consumer_missing_tenant_id",
                        extra={"routing_key": routing_key},
                    )
                    return

                should_provision = False
                if routing_key == "tenant.created":
                    should_provision = True
                elif routing_key == "tenant.status.changed":
                    to_status = payload.get("to_status", "")
                    should_provision = to_status == "provisioning"

                if should_provision:
                    tenant_id = UUID(str(tenant_id_raw))
                    logger.info(
                        "consumer_triggering_provisioning",
                        extra={"tenant_id": str(tenant_id), "routing_key": routing_key},
                    )
                    await self._start_provisioning(tenant_id)

            except Exception as exc:
                logger.exception(
                    "consumer_message_error",
                    extra={"error": str(exc)},
                )
