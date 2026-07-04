"""Add trigger_type to action_logs + create supplier_onboardings table

Revision ID: b3f9d2e1a7c4
Revises: eaa53ea69e7b
Create Date: 2026-06-19 10:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f9d2e1a7c4'
down_revision: Union[str, Sequence[str], None] = 'eaa53ea69e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    1. Add trigger_type column to action_logs (nullable with default 'MANUAL' for backwards compat)
    2. Create supplier_onboardings table for 90-day probation tracking
    """
    # ── 1. Add trigger_type to action_logs ─────────────────────────────────
    with op.batch_alter_table('action_logs') as batch_op:
        batch_op.add_column(
            sa.Column('trigger_type', sa.String(50), nullable=False, server_default='MANUAL')
        )

    # ── 2. Create supplier_onboardings table ───────────────────────────────
    op.create_table(
        'supplier_onboardings',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('supplier_id', sa.String(255), nullable=False),
        sa.Column('supplier_name', sa.String(255), nullable=False),

        # Dates
        sa.Column('application_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('probation_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('probation_end_date', sa.DateTime(timezone=True), nullable=True),

        # Status
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING_REVIEW'),

        # Assessment fields
        sa.Column('credentials_data', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('reference_check_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('geographic_risk_region', sa.String(100), nullable=True),
        sa.Column('capacity_info', sa.JSON(), nullable=False, server_default='{}'),

        # Live probation metrics
        sa.Column('probation_on_time_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('probation_rejection_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('probation_po_count', sa.Integer(), nullable=False, server_default='0'),

        # Audit
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_id'),
    )
    op.create_index('ix_supplier_onboardings_supplier_id', 'supplier_onboardings', ['supplier_id'])
    op.create_index('ix_supplier_onboardings_status', 'supplier_onboardings', ['status'])
    op.create_index('ix_supplier_onboardings_created_at', 'supplier_onboardings', ['created_at'])


def downgrade() -> None:
    """Reverse the migration."""
    op.drop_index('ix_supplier_onboardings_created_at', table_name='supplier_onboardings')
    op.drop_index('ix_supplier_onboardings_status', table_name='supplier_onboardings')
    op.drop_index('ix_supplier_onboardings_supplier_id', table_name='supplier_onboardings')
    op.drop_table('supplier_onboardings')

    with op.batch_alter_table('action_logs') as batch_op:
        batch_op.drop_column('trigger_type')
