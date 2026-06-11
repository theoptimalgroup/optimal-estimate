"""Add local sales pipeline tracking for processed eWorks quotes.

Revision ID: 032
Revises: 031
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_quote_sales_pipeline",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synced_quote_id", sa.Integer(), nullable=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=False),
        sa.Column("quote_ref", sa.String(length=100), nullable=True),
        sa.Column(
            "sales_bucket",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("sales_note", sa.Text(), nullable=True),
        sa.Column("assigned_sales_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_sales_email", sa.String(length=320), nullable=True),
        sa.Column("assigned_sales_name", sa.String(length=500), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bucket_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_reason", sa.String(length=100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eworks_quote_id", name="uq_processed_pipeline_eworks_quote_id"),
    )
    op.create_index(
        "ix_processed_pipeline_synced_quote_id",
        "processed_quote_sales_pipeline",
        ["synced_quote_id"],
    )
    op.create_index(
        "ix_processed_pipeline_sales_bucket",
        "processed_quote_sales_pipeline",
        ["sales_bucket"],
    )
    op.create_index(
        "ix_processed_pipeline_next_follow_up_at",
        "processed_quote_sales_pipeline",
        ["next_follow_up_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processed_pipeline_next_follow_up_at", table_name="processed_quote_sales_pipeline")
    op.drop_index("ix_processed_pipeline_sales_bucket", table_name="processed_quote_sales_pipeline")
    op.drop_index("ix_processed_pipeline_synced_quote_id", table_name="processed_quote_sales_pipeline")
    op.drop_table("processed_quote_sales_pipeline")
