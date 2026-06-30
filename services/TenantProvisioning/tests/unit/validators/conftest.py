"""Shared fixtures for validator unit tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.provisioning_job import ProvisioningJob


@pytest.fixture
def make_job():
    """Return a factory that builds a minimal ProvisioningJob with a given status."""
    def _make(status: str) -> ProvisioningJob:
        return ProvisioningJob(
            id=uuid4(),
            tenant_id=uuid4(),
            status=status,
            completed_steps=[],
            total_steps=8,
        )
    return _make
