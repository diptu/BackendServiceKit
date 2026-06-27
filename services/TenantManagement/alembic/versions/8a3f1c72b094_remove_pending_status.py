"""remove pending status

Revision ID: 8a3f1c72b094
Revises: 5f70f9cce1a5
Create Date: 2026-06-27 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8a3f1c72b094'
down_revision: Union[str, Sequence[str], None] = '5f70f9cce1a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Advance any pending tenants to active before dropping the value from the constraint.
    op.execute("UPDATE tenants SET status = 'active' WHERE status = 'pending'")
    op.drop_constraint(op.f('ck_tenants_valid_status'), 'tenants', type_='check')
    op.create_check_constraint(
        'valid_status',
        'tenants',
        "status IN ('draft','provisioning','active','suspended','archived','deleted')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_tenants_valid_status'), 'tenants', type_='check')
    op.create_check_constraint(
        'valid_status',
        'tenants',
        "status IN ('draft','provisioning','pending','active','suspended','archived','deleted')",
    )
