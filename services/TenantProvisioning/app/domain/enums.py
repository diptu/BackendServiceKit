"""Domain enumerations for provisioning jobs and resources."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepName(StrEnum):
    CREATE_SCHEMA = "create_schema"
    CREATE_STORAGE = "create_storage"
    CREATE_DEFAULT_ROLES = "create_default_roles"
    CREATE_DEFAULT_PERMISSIONS = "create_default_permissions"
    CREATE_ADMIN_USER = "create_admin_user"
    CREATE_WORKSPACE = "create_workspace"
    CONFIGURE_FEATURE_FLAGS = "configure_feature_flags"
    FINALIZE = "finalize"


class ResourceType(StrEnum):
    DATABASE_SCHEMA = "database_schema"
    STORAGE_BUCKET = "storage_bucket"
    DEFAULT_ROLES = "default_roles"
    DEFAULT_PERMISSIONS = "default_permissions"
    ADMIN_USER = "admin_user"
    WORKSPACE = "workspace"
    FEATURE_FLAGS = "feature_flags"


class ResourceStatus(StrEnum):
    PROVISIONED = "provisioned"
    PENDING = "pending"
    FAILED = "failed"


PROVISIONING_STEPS: list[StepName] = [
    StepName.CREATE_SCHEMA,
    StepName.CREATE_STORAGE,
    StepName.CREATE_DEFAULT_ROLES,
    StepName.CREATE_DEFAULT_PERMISSIONS,
    StepName.CREATE_ADMIN_USER,
    StepName.CREATE_WORKSPACE,
    StepName.CONFIGURE_FEATURE_FLAGS,
    StepName.FINALIZE,
]

STEP_TO_RESOURCE: dict[StepName, ResourceType | None] = {
    StepName.CREATE_SCHEMA: ResourceType.DATABASE_SCHEMA,
    StepName.CREATE_STORAGE: ResourceType.STORAGE_BUCKET,
    StepName.CREATE_DEFAULT_ROLES: ResourceType.DEFAULT_ROLES,
    StepName.CREATE_DEFAULT_PERMISSIONS: ResourceType.DEFAULT_PERMISSIONS,
    StepName.CREATE_ADMIN_USER: ResourceType.ADMIN_USER,
    StepName.CREATE_WORKSPACE: ResourceType.WORKSPACE,
    StepName.CONFIGURE_FEATURE_FLAGS: ResourceType.FEATURE_FLAGS,
    StepName.FINALIZE: None,
}
