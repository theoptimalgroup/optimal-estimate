"""Add local call-back tracking for eWorks Call Back quotes.

Revision ID: 033
Revises: 032
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "call_back_quote_tracking",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synced_quote_id", sa.Integer(), nullable=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=False),
        sa.Column("quote_ref", sa.String(length=100), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_name", sa.String(length=500), nullable=True),
        sa.Column("assigned_email", sa.String(length=320), nullable=True),
        sa.Column("call_note", sa.Text(), nullable=True),
        sa.Column("last_called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_call_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("call_status", sa.String(length=20), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eworks_quote_id", name="uq_call_back_tracking_eworks_quote_id"),
    )
    op.create_index("ix_call_back_tracking_synced_quote_id", "call_back_quote_tracking", ["synced_quote_id"])
    op.create_index("ix_call_back_tracking_next_call_at", "call_back_quote_tracking", ["next_call_at"])


def downgrade() -> None:
    op.drop_index("ix_call_back_tracking_next_call_at", table_name="call_back_quote_tracking")
    op.drop_index("ix_call_back_tracking_synced_quote_id", table_name="call_back_quote_tracking")
    op.drop_table("call_back_quote_tracking")
