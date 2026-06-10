"""Add shared quote-level Step 2 work block snapshots.

Revision ID: 031
Revises: 030
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_work_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_ref", sa.String(length=100), nullable=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=True),
        sa.Column("synced_quote_id", sa.Integer(), nullable=True),
        sa.Column("step2_snapshot", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_email", sa.String(length=320), nullable=True),
        sa.Column("updated_by_name", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["synced_quote_id"], ["eworks_quotes.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_work_snapshots_quote_ref", "quote_work_snapshots", ["quote_ref"])
    op.create_index("ix_quote_work_snapshots_eworks_quote_id", "quote_work_snapshots", ["eworks_quote_id"])
    op.create_index("ix_quote_work_snapshots_synced_quote_id", "quote_work_snapshots", ["synced_quote_id"])
    op.create_index(
        "ix_quote_work_snapshots_quote_keys",
        "quote_work_snapshots",
        ["eworks_quote_id", "quote_ref"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_quote_work_snapshots_quote_keys", table_name="quote_work_snapshots")
    op.drop_index("ix_quote_work_snapshots_synced_quote_id", table_name="quote_work_snapshots")
    op.drop_index("ix_quote_work_snapshots_eworks_quote_id", table_name="quote_work_snapshots")
    op.drop_index("ix_quote_work_snapshots_quote_ref", table_name="quote_work_snapshots")
    op.drop_table("quote_work_snapshots")
