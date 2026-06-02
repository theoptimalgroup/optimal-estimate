"""Add eworks_customer_snapshot to calculation_sessions.

Revision ID: 009
Revises: 008
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calculation_sessions",
        sa.Column("eworks_customer_snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calculation_sessions", "eworks_customer_snapshot")
