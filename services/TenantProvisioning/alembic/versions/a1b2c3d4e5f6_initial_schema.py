"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provisioning_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("completed_steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provisioning_jobs")),
    )
    op.create_index(
        op.f("idx_provisioning_jobs_tenant_id"), "provisioning_jobs", ["tenant_id"]
    )
    op.create_index(
        op.f("idx_provisioning_jobs_status"), "provisioning_jobs", ["status"]
    )
    op.create_index(
        "idx_provisioning_jobs_tenant_created",
        "provisioning_jobs",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "provisioning_resources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="provisioned"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["provisioning_jobs.id"],
            name=op.f("fk_provisioning_resources_job_id_provisioning_jobs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provisioning_resources")),
    )
    op.create_index(
        op.f("idx_provisioning_resources_tenant_id"),
        "provisioning_resources",
        ["tenant_id"],
    )
    op.create_index(
        op.f("idx_provisioning_resources_job_id"),
        "provisioning_resources",
        ["job_id"],
    )
    op.create_index(
        "idx_provisioning_resources_tenant_type",
        "provisioning_resources",
        ["tenant_id", "resource_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_provisioning_resources_tenant_type", "provisioning_resources")
    op.drop_index(
        op.f("idx_provisioning_resources_job_id"), "provisioning_resources"
    )
    op.drop_index(
        op.f("idx_provisioning_resources_tenant_id"), "provisioning_resources"
    )
    op.drop_table("provisioning_resources")

    op.drop_index("idx_provisioning_jobs_tenant_created", "provisioning_jobs")
    op.drop_index(op.f("idx_provisioning_jobs_status"), "provisioning_jobs")
    op.drop_index(op.f("idx_provisioning_jobs_tenant_id"), "provisioning_jobs")
    op.drop_table("provisioning_jobs")
