"""Import every ORM model so Base.metadata sees all tables."""

from __future__ import annotations

from app.models.provisioning_job import ProvisioningJob

__all__ = ["ProvisioningJob"]
