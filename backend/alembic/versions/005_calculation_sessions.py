"""Add calculation_sessions for eWorks link flow.

Revision ID: 005
Revises: 004
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("payload_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("step1_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("step2_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trades.id"), nullable=True),
        sa.Column("rate_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rate_rules.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_calculation_sessions_session_token", "calculation_sessions", ["session_token"], unique=True)
    op.create_index("ix_calculation_sessions_expires_at", "calculation_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_calculation_sessions_expires_at", table_name="calculation_sessions")
    op.drop_index("ix_calculation_sessions_session_token", table_name="calculation_sessions")
    op.drop_table("calculation_sessions")
