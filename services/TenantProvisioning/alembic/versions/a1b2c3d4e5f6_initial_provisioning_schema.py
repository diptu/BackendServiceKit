"""initial provisioning schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-07-11 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provisioning_jobs",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("subdomain", sa.String(length=63), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_step", sa.String(length=40), nullable=True),
        sa.Column("db_name", sa.String(length=255), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("tenant_id", name=op.f("pk_provisioning_jobs")),
    )
    op.create_index("idx_provisioning_jobs_status", "provisioning_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_provisioning_jobs_status", table_name="provisioning_jobs")
    op.drop_table("provisioning_jobs")
