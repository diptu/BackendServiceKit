"""initial session schema

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
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index("idx_sessions_tenant_user", "sessions", ["tenant_id", "user_id"])


def downgrade() -> None:
    op.drop_index("idx_sessions_tenant_user", table_name="sessions")
    op.drop_table("sessions")
