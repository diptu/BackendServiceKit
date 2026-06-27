"""add pending status

Revision ID: 5f70f9cce1a5
Revises: 35cabc56b647
Create Date: 2026-06-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5f70f9cce1a5'
down_revision: Union[str, Sequence[str], None] = 'c3c86a584056'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use op.f() so the already-prefixed name is used as-is (no convention re-applied).
    op.drop_constraint(op.f('ck_tenants_valid_status'), 'tenants', type_='check')
    op.create_check_constraint(
        'valid_status',
        'tenants',
        "status IN ('draft','provisioning','pending','active','suspended','archived','deleted')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_tenants_valid_status'), 'tenants', type_='check')
    op.create_check_constraint(
        'valid_status',
        'tenants',
        "status IN ('draft','provisioning','active','suspended','archived','deleted')",
    )
