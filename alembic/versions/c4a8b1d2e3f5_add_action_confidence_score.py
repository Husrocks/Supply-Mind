"""Add confidence_score to action_logs

Revision ID: c4a8b1d2e3f5
Revises: b3f9d2e1a7c4
Create Date: 2026-06-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4a8b1d2e3f5"
down_revision: Union[str, None] = "b3f9d2e1a7c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "action_logs",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("action_logs", "confidence_score")
