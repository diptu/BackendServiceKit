"""Celery application — shared by all task modules."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "api_gateway",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.audit_tasks",
        "app.tasks.cache_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
)
