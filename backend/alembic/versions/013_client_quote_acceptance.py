"""Add client quote acceptance fields to calculation_sessions.

Revision ID: 013
Revises: 012
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calculation_sessions",
        sa.Column("client_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("client_acceptance_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("client_acceptance_email", sa.String(255), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("client_acceptance_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("client_acceptance_ip", sa.String(100), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("client_acceptance_user_agent", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_calculation_sessions_client_accepted_at",
        "calculation_sessions",
        ["client_accepted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_sessions_client_accepted_at", table_name="calculation_sessions")
    op.drop_column("calculation_sessions", "client_acceptance_user_agent")
    op.drop_column("calculation_sessions", "client_acceptance_ip")
    op.drop_column("calculation_sessions", "client_acceptance_notes")
    op.drop_column("calculation_sessions", "client_acceptance_email")
    op.drop_column("calculation_sessions", "client_acceptance_name")
    op.drop_column("calculation_sessions", "client_accepted_at")
