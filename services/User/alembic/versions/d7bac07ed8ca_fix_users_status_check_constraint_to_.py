"""fix users status check constraint to include locked

Revision ID: d7bac07ed8ca
Revises: 93ff0f3c1d98
Create Date: 2026-07-06 01:58:01.533647

The earlier merge migration added `locked_reason`/`locked_by` columns but
never touched the CHECK constraint on `status` itself — a real bug caught
by real Docker verification, not by the test suite (SQLite doesn't enforce
CHECK constraints the same way, so this passed cleanly there). The
constraint predates this merge (created under UserManagement, oddly named
`ck_users_ck_users_valid_status`, likely a doubled-prefix artifact from
that original build) and only allowed pending/active/suspended/deactivated
— `locked` transitions failed with a real IntegrityError against Postgres.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "d7bac07ed8ca"
down_revision: Union[str, None] = "93ff0f3c1d98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # op.f() marks the name as already-final — without it, drop_constraint
    # re-applies the naming-convention template to whatever string is
    # passed, doubling the "ck_users_" prefix a second time (caught by
    # this exact migration failing against the real database on first try).
    op.drop_constraint(op.f("ck_users_ck_users_valid_status"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_valid_status"),
        "users",
        "status IN ('pending','active','suspended','locked','deactivated')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_valid_status"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_ck_users_valid_status"),
        "users",
        "status IN ('pending','active','suspended','deactivated')",
    )
