"""initial tables

Revision ID: c3c86a584056
Revises: 
Create Date: 2026-06-27 20:06:34.734152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3c86a584056'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tenant_lifecycle_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False, comment='Tenant this event belongs to.'),
    sa.Column('from_status', sa.String(length=50), nullable=True, comment='Status before this transition. NULL for the initial activation.'),
    sa.Column('to_status', sa.String(length=50), nullable=False, comment='Status after this transition.'),
    sa.Column('transition', sa.String(length=50), nullable=False, comment='Named transition action (activate, suspend, lock, archive, delete).'),
    sa.Column('reason', sa.String(length=500), nullable=True, comment='Human-readable reason provided by the caller.'),
    sa.Column('performed_by', sa.Uuid(), nullable=True, comment='UUID of the actor who triggered the transition. NULL for system events.'),
    sa.Column('source', sa.String(length=100), nullable=False, comment="Originating source: 'api', 'event:subscription.expired', etc."),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='When the transition occurred (UTC).'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tenant_lifecycle_events'))
    )
    op.create_index('idx_lifecycle_events_tenant_occurred', 'tenant_lifecycle_events', ['tenant_id', 'occurred_at'], unique=False)
    op.create_index(op.f('ix_tenant_lifecycle_events_tenant_id'), 'tenant_lifecycle_events', ['tenant_id'], unique=False)
    op.create_table('tenant_lifecycle_states',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False, comment='External tenant identifier. Not a FK — projection pattern.'),
    sa.Column('current_status', sa.String(length=50), nullable=False, comment='Current lifecycle state.'),
    sa.Column('previous_status', sa.String(length=50), nullable=True, comment='Status before the most recent transition.'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tenant_lifecycle_states')),
    sa.UniqueConstraint('tenant_id', name=op.f('uq_tenant_lifecycle_states_tenant_id'))
    )
    op.create_index('idx_lifecycle_states_tenant_id', 'tenant_lifecycle_states', ['tenant_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_lifecycle_states_tenant_id', table_name='tenant_lifecycle_states')
    op.drop_table('tenant_lifecycle_states')
    op.drop_index(op.f('ix_tenant_lifecycle_events_tenant_id'), table_name='tenant_lifecycle_events')
    op.drop_index('idx_lifecycle_events_tenant_occurred', table_name='tenant_lifecycle_events')
    op.drop_table('tenant_lifecycle_events')
