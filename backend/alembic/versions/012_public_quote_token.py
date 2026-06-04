"""Add public quote sharing token fields to calculation_sessions.

Revision ID: 012
Revises: 011
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calculation_sessions", sa.Column("public_quote_token", sa.String(64), nullable=True))
    op.add_column(
        "calculation_sessions",
        sa.Column("public_quote_token_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("public_quote_token_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("public_quote_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_calculation_sessions_public_quote_token",
        "calculation_sessions",
        ["public_quote_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_sessions_public_quote_token", table_name="calculation_sessions")
    op.drop_column("calculation_sessions", "public_quote_expires_at")
    op.drop_column("calculation_sessions", "public_quote_token_revoked_at")
    op.drop_column("calculation_sessions", "public_quote_token_created_at")
    op.drop_column("calculation_sessions", "public_quote_token")
