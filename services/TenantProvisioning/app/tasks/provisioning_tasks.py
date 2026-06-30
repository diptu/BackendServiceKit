"""Celery task that executes all 8 provisioning steps sequentially.

Each step:
  1. Updates the job's current_step in the DB.
  2. Simulates work (in production: calls real infra APIs).
  3. Creates a ProvisioningResource record.
  4. Commits so polling callers see live progress.

On completion, calls TenantLifecycle's PUT /pending (fire-and-log).
On any step failure, marks the job as failed and returns.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import (
    PROVISIONING_STEPS,
    STEP_TO_RESOURCE,
    JobStatus,
    ResourceStatus,
    StepName,
)
from app.domain.events import ProvisioningCompleted, ProvisioningFailed
from app.events.provisioning_events import EventPublisher, publish_event
from app.infrastructure.clients.tenant_lifecycle import TenantLifecycleClient
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.messaging.publisher import NullPublisher, RabbitMQPublisher
from app.models.provisioning_resource import ProvisioningResource
from app.repositories.provisioning_job import ProvisioningJobRepository
from app.repositories.provisioning_resource import ProvisioningResourceRepository
from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


async def _connect_publisher() -> tuple[EventPublisher, Any]:
    """Open a short-lived aio_pika connection for event publishing inside a Celery task.

    Returns (NullPublisher, None) when RabbitMQ is unavailable — never raises.
    The caller is responsible for closing the returned connection when not None.
    """
    try:
        import aio_pika

        conn = await aio_pika.connect_robust(settings.rabbitmq_url, timeout=3.0)
        return RabbitMQPublisher(conn), conn
    except Exception as exc:
        logger.warning("task_publisher_unavailable", extra={"error": str(exc)})
        return NullPublisher(), None


@celery_app.task(
    bind=True,
    name="tenant_provisioning.run_provisioning",
    max_retries=3,
    acks_late=True,
    default_retry_delay=60,
    autoretry_for=(OSError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def run_provisioning(self: object, job_id: str, tenant_id: str) -> dict[str, str]:
    return asyncio.run(_provision_async(UUID(job_id), UUID(tenant_id)))


@celery_app.task(
    bind=True,
    name="tenant_provisioning.rollback_provisioning",
    max_retries=2,
    acks_late=True,
    default_retry_delay=30,
)
def rollback_provisioning(self: object, job_id: str, tenant_id: str) -> dict[str, str]:
    return asyncio.run(_rollback_async(UUID(job_id), UUID(tenant_id)))


async def _provision_async(job_id: UUID, tenant_id: UUID) -> dict[str, str]:
    publisher, pub_conn = await _connect_publisher()
    try:
        async with SessionLocal() as session:
            job_repo = ProvisioningJobRepository(session)
            resource_repo = ProvisioningResourceRepository(session)

            await job_repo.update_status(
                job_id,
                status=JobStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                completed_steps=[],
            )
            await session.commit()

            completed: list[str] = []

            for step in PROVISIONING_STEPS:
                try:
                    logger.info(
                        "provisioning_step_started",
                        extra={"job_id": str(job_id), "tenant_id": str(tenant_id), "step": step},
                    )
                    await job_repo.update_status(
                        job_id,
                        status=JobStatus.RUNNING,
                        current_step=step,
                        completed_steps=completed,
                    )
                    await session.commit()

                    if step == StepName.FINALIZE:
                        await _finalize(job_id, tenant_id, job_repo, session, publisher)
                    else:
                        await _execute_step(step, job_id, tenant_id, resource_repo, session)

                    completed.append(step)
                    logger.info(
                        "provisioning_step_completed",
                        extra={"job_id": str(job_id), "step": step},
                    )

                except Exception as exc:
                    logger.exception(
                        "provisioning_step_failed",
                        extra={"job_id": str(job_id), "step": step, "error": str(exc)},
                    )
                    async with SessionLocal() as err_session:
                        err_repo = ProvisioningJobRepository(err_session)
                        await err_repo.update_status(
                            job_id,
                            status=JobStatus.FAILED,
                            current_step=step,
                            completed_steps=completed,
                            error_message=f"Step '{step}' failed: {exc}",
                            completed_at=datetime.now(timezone.utc),
                        )
                        await err_session.commit()
                    await publish_event(
                        ProvisioningFailed(
                            tenant_id=tenant_id,
                            job_id=job_id,
                            failed_step=str(step),
                            error_message=str(exc),
                        ),
                        publisher,
                    )
                    rollback_provisioning.apply_async(
                        args=[str(job_id), str(tenant_id)],
                        countdown=5,
                    )
                    return {"status": "failed", "job_id": str(job_id), "failed_step": str(step)}
    finally:
        if pub_conn is not None:
            await pub_conn.close()

    return {"status": "completed", "job_id": str(job_id)}


async def _execute_step(
    step: StepName,
    job_id: UUID,
    tenant_id: UUID,
    resource_repo: ProvisioningResourceRepository,
    session: AsyncSession,
) -> None:
    resource_type = STEP_TO_RESOURCE.get(step)
    if resource_type is None:
        return

    now = datetime.now(timezone.utc)
    resource = ProvisioningResource(
        id=uuid4(),
        job_id=job_id,
        tenant_id=tenant_id,
        resource_type=resource_type.value,
        resource_id=f"{resource_type.value}_{tenant_id}",
        status=ResourceStatus.PROVISIONED.value,
        meta={"step": step, "provisioned_at": now.isoformat()},
        provisioned_at=now,
    )
    await resource_repo.create(resource)
    await session.commit()


async def _finalize(
    job_id: UUID,
    tenant_id: UUID,
    job_repo: ProvisioningJobRepository,
    session: AsyncSession,
    publisher: EventPublisher,
) -> None:
    now = datetime.now(timezone.utc)
    await job_repo.update_status(
        job_id,
        status=JobStatus.COMPLETED,
        current_step=None,
        completed_steps=[s.value for s in PROVISIONING_STEPS],
        completed_at=now,
    )
    await session.commit()

    tl_client = TenantLifecycleClient()
    await tl_client.advance_to_pending(tenant_id, reason="Provisioning completed")

    await publish_event(
        ProvisioningCompleted(tenant_id=tenant_id, job_id=job_id),
        publisher,
    )

    logger.info(
        "provisioning_finalized",
        extra={"job_id": str(job_id), "tenant_id": str(tenant_id)},
    )


async def _rollback_async(job_id: UUID, tenant_id: UUID) -> dict[str, str]:
    """Mark all resources for a failed job as FAILED and log rollback completion."""
    from app.domain.enums import ResourceStatus

    logger.info(
        "provisioning_rollback_started",
        extra={"job_id": str(job_id), "tenant_id": str(tenant_id)},
    )
    async with SessionLocal() as session:
        resource_repo = ProvisioningResourceRepository(session)
        resources = await resource_repo.list_by_job_id(job_id)
        for resource in resources:
            resource.status = ResourceStatus.FAILED.value
        await session.commit()

    logger.info(
        "provisioning_rollback_completed",
        extra={
            "job_id": str(job_id),
            "tenant_id": str(tenant_id),
            "rolled_back_count": len(resources),
        },
    )
    return {
        "status": "rolled_back",
        "job_id": str(job_id),
        "rolled_back_count": str(len(resources)),
    }
