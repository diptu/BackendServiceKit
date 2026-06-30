"""Celery application for async provisioning job execution."""

from __future__ import annotations

from kombu import Exchange, Queue  # type: ignore[import-untyped]

from celery import Celery

from app.core.config import settings

_default_exchange = Exchange("celery", type="direct")
_dlx_exchange = Exchange("celery.dlx", type="direct")

celery_app = Celery(
    "tenant_provisioning",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.provisioning_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_queues=(
        Queue(
            "celery",
            _default_exchange,
            routing_key="celery",
            queue_arguments={
                "x-dead-letter-exchange": "celery.dlx",
                "x-dead-letter-routing-key": "celery.dead",
            },
        ),
        Queue(
            "celery.dead",
            _dlx_exchange,
            routing_key="celery.dead",
        ),
    ),
    task_default_queue="celery",
    task_default_exchange="celery",
    task_default_routing_key="celery",
)
