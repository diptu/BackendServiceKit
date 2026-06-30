"""Unit tests for the provisioning events module."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from app.domain.events import (
    ProvisioningCompleted,
    ProvisioningFailed,
    ProvisioningStarted,
    ProvisioningStepCompleted,
)
from app.events.provisioning_events import publish_event


class _RecordingPublisher:
    """Test double that captures publish calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        self.calls.append((routing_key, payload))


# ── routing key resolution ────────────────────────────────────────────────────

async def test_provisioning_started_routing_key() -> None:
    publisher = _RecordingPublisher()
    event = ProvisioningStarted(tenant_id=uuid4(), job_id=uuid4())
    await publish_event(event, publisher)
    assert len(publisher.calls) == 1
    assert publisher.calls[0][0] == "provisioning.job.started"


async def test_provisioning_completed_routing_key() -> None:
    publisher = _RecordingPublisher()
    event = ProvisioningCompleted(tenant_id=uuid4(), job_id=uuid4())
    await publish_event(event, publisher)
    assert publisher.calls[0][0] == "provisioning.job.completed"


async def test_provisioning_failed_routing_key() -> None:
    publisher = _RecordingPublisher()
    event = ProvisioningFailed(
        tenant_id=uuid4(),
        job_id=uuid4(),
        failed_step="create_schema",
        error_message="timeout",
    )
    await publish_event(event, publisher)
    assert publisher.calls[0][0] == "provisioning.job.failed"


async def test_provisioning_step_completed_routing_key() -> None:
    publisher = _RecordingPublisher()
    event = ProvisioningStepCompleted(tenant_id=uuid4(), job_id=uuid4(), step_name="create_schema")
    await publish_event(event, publisher)
    assert publisher.calls[0][0] == "provisioning.job.step_completed"


# ── payload serialization ─────────────────────────────────────────────────────

async def test_started_payload_contains_tenant_and_job_ids() -> None:
    publisher = _RecordingPublisher()
    tenant_id = uuid4()
    job_id = uuid4()
    await publish_event(ProvisioningStarted(tenant_id=tenant_id, job_id=job_id), publisher)
    payload = publisher.calls[0][1]
    assert str(tenant_id) in str(payload["tenant_id"])
    assert str(job_id) in str(payload["job_id"])


async def test_failed_payload_contains_step_and_error() -> None:
    publisher = _RecordingPublisher()
    await publish_event(
        ProvisioningFailed(
            tenant_id=uuid4(),
            job_id=uuid4(),
            failed_step="create_storage",
            error_message="bucket quota exceeded",
        ),
        publisher,
    )
    payload = publisher.calls[0][1]
    assert payload["failed_step"] == "create_storage"
    assert payload["error_message"] == "bucket quota exceeded"


async def test_payload_includes_event_id_and_timestamp() -> None:
    publisher = _RecordingPublisher()
    await publish_event(ProvisioningCompleted(tenant_id=uuid4(), job_id=uuid4()), publisher)
    payload = publisher.calls[0][1]
    assert "event_id" in payload
    assert "timestamp" in payload


# ── unknown event type ────────────────────────────────────────────────────────

async def test_unknown_event_type_is_silently_dropped() -> None:
    publisher = _RecordingPublisher()

    class _UnknownEvent:
        pass

    await publish_event(_UnknownEvent(), publisher)
    assert publisher.calls == []


# ── publisher contract ────────────────────────────────────────────────────────

async def test_publish_event_calls_publisher_exactly_once() -> None:
    publisher = _RecordingPublisher()
    await publish_event(ProvisioningStarted(tenant_id=uuid4(), job_id=uuid4()), publisher)
    await publish_event(ProvisioningCompleted(tenant_id=uuid4(), job_id=uuid4()), publisher)
    assert len(publisher.calls) == 2


async def test_null_publisher_does_not_raise() -> None:
    from app.infrastructure.messaging.publisher import NullPublisher
    await publish_event(ProvisioningStarted(tenant_id=uuid4(), job_id=uuid4()), NullPublisher())
