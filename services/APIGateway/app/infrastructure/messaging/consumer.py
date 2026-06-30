"""RabbitMQ consumer — listens for tenant change events and invalidates cache."""

from __future__ import annotations

import asyncio
import json
import logging

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from app.core.config import settings

logger = logging.getLogger(__name__)


class TenantEventConsumer:
    """Subscribes to the tenant.events exchange and triggers cache invalidation.

    Event routing keys consumed:
      tenant.status.changed  — emitted by TenantManagement on any status update
      tenant.updated         — emitted by TenantManagement on data mutations
      tenant-lifecycle.*     — emitted by TenantLifecycle on state transitions

    On each event, the consumer calls back into the CacheService to purge the
    affected tenant's cache keys so subsequent GET requests fetch fresh data.
    """

    def __init__(
        self,
        connection: AbstractRobustConnection,
        on_invalidate: "Callable[[str], Awaitable[int]]",  # type: ignore[name-defined]  # noqa: F821
    ) -> None:
        self._connection = connection
        self._on_invalidate = on_invalidate
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="tenant-event-consumer")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        try:
            async with self._connection.channel() as channel:
                await channel.set_qos(prefetch_count=10)

                # Declare the upstream exchange (must match TM/TL config)
                exchange = await channel.declare_exchange(
                    settings.rabbitmq_tenant_events_exchange,
                    ExchangeType.TOPIC,
                    durable=True,
                )

                queue = await channel.declare_queue(
                    settings.rabbitmq_tenant_events_queue,
                    durable=True,
                )

                # Bind to all tenant-related routing keys
                for routing_key in (
                    "tenant.status.changed",
                    "tenant.updated",
                    "tenant-lifecycle.*",
                ):
                    await queue.bind(exchange, routing_key=routing_key)

                logger.info(
                    "consumer_started",
                    extra={
                        "exchange": settings.rabbitmq_tenant_events_exchange,
                        "queue": settings.rabbitmq_tenant_events_queue,
                    },
                )

                async with queue.iterator() as messages:
                    async for message in messages:
                        await self._handle(message)

        except asyncio.CancelledError:
            logger.info("consumer_stopped")
        except Exception as exc:
            logger.error(
                "consumer_error",
                extra={"error": str(exc)},
                exc_info=True,
            )

    async def _handle(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                payload = json.loads(message.body)
                tenant_id: str | None = (
                    payload.get("tenant_id")
                    or payload.get("id")
                )
                if tenant_id:
                    deleted = await self._on_invalidate(str(tenant_id))
                    logger.info(
                        "cache_invalidated_by_event",
                        extra={
                            "tenant_id": tenant_id,
                            "routing_key": message.routing_key,
                            "keys_deleted": deleted,
                        },
                    )
            except Exception as exc:
                logger.warning(
                    "consumer_handle_error",
                    extra={"error": str(exc), "body": message.body[:200]},
                )
