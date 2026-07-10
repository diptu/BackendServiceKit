"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class ProvisioningStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEPROVISIONED = "deprovisioned"


class ProvisioningStep(StrEnum):
    CREATE_DATABASE = "create_database"
    RUN_MIGRATIONS = "run_migrations"
    REGISTER_CONTROL_PLANE = "register_control_plane"
    DONE = "done"
