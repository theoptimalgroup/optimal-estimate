"""Add eWorks acceptance sync tracking fields to calculation_sessions.

Revision ID: 014
Revises: 013
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calculation_sessions",
        sa.Column("eworks_acceptance_sync_status", sa.String(32), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("eworks_acceptance_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("eworks_acceptance_sync_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column(
            "eworks_acceptance_sync_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("eworks_acceptance_last_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("eworks_acceptance_last_response", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_calculation_sessions_eworks_acceptance_sync_status",
        "calculation_sessions",
        ["eworks_acceptance_sync_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_calculation_sessions_eworks_acceptance_sync_status",
        table_name="calculation_sessions",
    )
    op.drop_column("calculation_sessions", "eworks_acceptance_last_response")
    op.drop_column("calculation_sessions", "eworks_acceptance_last_payload")
    op.drop_column("calculation_sessions", "eworks_acceptance_sync_attempts")
    op.drop_column("calculation_sessions", "eworks_acceptance_sync_error")
    op.drop_column("calculation_sessions", "eworks_acceptance_synced_at")
    op.drop_column("calculation_sessions", "eworks_acceptance_sync_status")
