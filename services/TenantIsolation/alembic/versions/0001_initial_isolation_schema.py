"""Initial isolation schema.

Revision ID: 0001
Revises:
Create Date: 2026-06-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "isolation_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("policy_type", sa.String(50), nullable=False, server_default="strict"),
        sa.Column("allow_cross_tenant_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allowed_partner_tenant_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.PrimaryKeyConstraint("id", name="pk_isolation_policies"),
    )
    op.create_index("idx_isolation_policies_tenant_id", "isolation_policies", ["tenant_id"])
    op.create_index(
        "idx_isolation_policies_tenant_active", "isolation_policies", ["tenant_id", "is_active"]
    )

    op.create_table(
        "resource_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.String(500), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("source_service", sa.String(200), nullable=False),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resource_claims"),
        sa.UniqueConstraint(
            "resource_type", "resource_id", name="uq_resource_claims_type_id"
        ),
    )
    op.create_index("idx_resource_claims_tenant_id", "resource_claims", ["tenant_id"])
    op.create_index(
        "idx_resource_claims_type_id", "resource_claims", ["resource_type", "resource_id"]
    )

    op.create_table(
        "access_decision_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("caller_tenant_id", sa.Uuid(), nullable=False),
        sa.Column("target_tenant_id", sa.Uuid(), nullable=True),
        sa.Column("resource_id", sa.String(500), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_access_decision_logs"),
    )
    op.create_index(
        "idx_access_decision_logs_caller_tenant", "access_decision_logs", ["caller_tenant_id"]
    )
    op.create_index(
        "idx_access_decision_logs_decided_at", "access_decision_logs", ["decided_at"]
    )
    op.create_index(
        "idx_access_decision_logs_decision", "access_decision_logs", ["decision"]
    )


def downgrade() -> None:
    op.drop_table("access_decision_logs")
    op.drop_table("resource_claims")
    op.drop_table("isolation_policies")
