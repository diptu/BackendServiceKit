"""add abac_policies table

Revision ID: a3f5c9d1e7b2
Revises: d2d396cf5a68
Create Date: 2026-07-06 03:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f5c9d1e7b2"
down_revision: Union[str, Sequence[str], None] = "d2d396cf5a68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "abac_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
            comment="Owning tenant (projection — not a FK to Tenent's database).",
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("effect", sa.String(length=10), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Set on soft-delete; NULL means not deleted.",
        ),
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
        sa.CheckConstraint(
            "effect IN ('allow','deny')",
            name=op.f("ck_abac_policies_ck_abac_policies_valid_effect"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_abac_policies")),
    )
    op.create_index(
        "idx_abac_policies_tenant_name",
        "abac_policies",
        ["tenant_id", "name"],
        unique=True,
    )
    op.create_index(
        "idx_abac_policies_tenant_resource_action",
        "abac_policies",
        ["tenant_id", "resource_type", "action", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "idx_abac_policies_tenant_resource_action", table_name="abac_policies"
    )
    op.drop_index("idx_abac_policies_tenant_name", table_name="abac_policies")
    op.drop_table("abac_policies")
