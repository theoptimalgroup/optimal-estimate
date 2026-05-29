"""Add status and submitted_at to calculation_sessions.

Revision ID: 008
Revises: 007
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calculation_sessions",
        sa.Column("status", sa.String(32), nullable=False, server_default="in_progress"),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_calculation_sessions_status", "calculation_sessions", ["status"])
    op.create_index("ix_calculation_sessions_submitted_at", "calculation_sessions", ["submitted_at"])


def downgrade() -> None:
    op.drop_index("ix_calculation_sessions_submitted_at", table_name="calculation_sessions")
    op.drop_index("ix_calculation_sessions_status", table_name="calculation_sessions")
    op.drop_column("calculation_sessions", "submitted_at")
    op.drop_column("calculation_sessions", "status")
