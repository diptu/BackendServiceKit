"""mfa, oauth2.1 and sso tables

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-07-10 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ MFA
    op.create_table(
        "mfa_secrets",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("tenant_id", "user_id", name=op.f("pk_mfa_secrets")),
    )

    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mfa_recovery_codes")),
        sa.UniqueConstraint("code_hash", name=op.f("uq_mfa_recovery_codes_code_hash")),
    )
    op.create_index(
        "idx_mfa_recovery_codes_tenant_user",
        "mfa_recovery_codes",
        ["tenant_id", "user_id"],
    )

    op.create_table(
        "mfa_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mfa_challenges")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_mfa_challenges_token_hash")),
    )
    op.create_index(
        "idx_mfa_challenges_tenant_user",
        "mfa_challenges",
        ["tenant_id", "user_id"],
    )

    # --------------------------------------------------------------- OAuth2.1
    op.create_table(
        "oauth_clients",
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_confidential", sa.Boolean(), nullable=False),
        sa.Column("client_secret_hash", sa.String(length=64), nullable=True),
        sa.Column("redirect_uris", sa.JSON(), nullable=False),
        sa.Column("allowed_scopes", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("client_id", name=op.f("pk_oauth_clients")),
    )
    op.create_index("idx_oauth_clients_tenant", "oauth_clients", ["tenant_id"])

    op.create_table(
        "oauth_authorization_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("code_challenge", sa.String(length=128), nullable=True),
        sa.Column("code_challenge_method", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_authorization_codes")),
        sa.UniqueConstraint(
            "code_hash", name=op.f("uq_oauth_authorization_codes_code_hash")
        ),
    )
    op.create_index(
        "idx_oauth_auth_codes_tenant", "oauth_authorization_codes", ["tenant_id"]
    )

    # -------------------------------------------------------------------- SSO
    op.create_table(
        "sso_states",
        sa.Column("state", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("state", name=op.f("pk_sso_states")),
    )
    op.create_index("idx_sso_states_tenant", "sso_states", ["tenant_id"])

    op.create_table(
        "sso_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sso_identities")),
    )
    op.create_index(
        "idx_sso_identities_lookup",
        "sso_identities",
        ["tenant_id", "provider", "subject"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_sso_identities_lookup", table_name="sso_identities")
    op.drop_table("sso_identities")
    op.drop_index("idx_sso_states_tenant", table_name="sso_states")
    op.drop_table("sso_states")
    op.drop_index("idx_oauth_auth_codes_tenant", table_name="oauth_authorization_codes")
    op.drop_table("oauth_authorization_codes")
    op.drop_index("idx_oauth_clients_tenant", table_name="oauth_clients")
    op.drop_table("oauth_clients")
    op.drop_index("idx_mfa_challenges_tenant_user", table_name="mfa_challenges")
    op.drop_table("mfa_challenges")
    op.drop_index("idx_mfa_recovery_codes_tenant_user", table_name="mfa_recovery_codes")
    op.drop_table("mfa_recovery_codes")
    op.drop_table("mfa_secrets")
