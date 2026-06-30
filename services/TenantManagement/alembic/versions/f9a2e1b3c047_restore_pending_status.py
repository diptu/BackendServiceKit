"""restore pending status to check constraint

Revision ID: f9a2e1b3c047
Revises: 8a3f1c72b094
Create Date: 2026-06-30 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f9a2e1b3c047"
down_revision: Union[str, Sequence[str], None] = "8a3f1c72b094"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("valid_status", "tenants", type_="check")
    op.create_check_constraint(
        "ck_tenants_valid_status",
        "tenants",
        "status IN ('draft','provisioning','pending','active','suspended','archived','deleted')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenants_valid_status", "tenants", type_="check")
    op.create_check_constraint(
        "valid_status",
        "tenants",
        "status IN ('draft','provisioning','active','suspended','archived','deleted')",
    )
