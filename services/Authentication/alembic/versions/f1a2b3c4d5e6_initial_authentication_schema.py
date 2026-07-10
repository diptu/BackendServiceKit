"""initial authentication schema

Revision ID: f1a2b3c4d5e6
Revises:
Create Date: 2026-07-06 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credentials",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "password_algorithm",
            sa.String(length=20),
            nullable=False,
            server_default="argon2id",
        ),
        sa.Column(
            "failed_login_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_credentials")),
    )
    op.create_index(
        "idx_credentials_tenant_email",
        "credentials",
        ["tenant_id", "email"],
        unique=True,
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        "idx_refresh_tokens_tenant_user", "refresh_tokens", ["tenant_id", "user_id"]
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint(
            "token_hash", name=op.f("uq_password_reset_tokens_token_hash")
        ),
    )
    op.create_index(
        "idx_password_reset_tokens_user", "password_reset_tokens", ["user_id"]
    )

    op.create_table(
        "auth_events",
        sa.Column("seq", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("seq", name=op.f("pk_auth_events")),
        sa.UniqueConstraint("id", name=op.f("uq_auth_events_id")),
    )
    op.create_index(
        "idx_auth_events_tenant_user_occurred",
        "auth_events",
        ["tenant_id", "user_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_auth_events_tenant_user_occurred", table_name="auth_events")
    op.drop_table("auth_events")
    op.drop_index("idx_password_reset_tokens_user", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("idx_refresh_tokens_tenant_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("idx_credentials_tenant_email", table_name="credentials")
    op.drop_table("credentials")
