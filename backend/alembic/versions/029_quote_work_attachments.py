"""Add shared quote work block attachments table.

Revision ID: 029
Revises: 028
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_work_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_id", sa.String(length=64), nullable=False),
        sa.Column("quote_ref", sa.String(length=100), nullable=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=True),
        sa.Column("synced_quote_id", sa.Integer(), nullable=True),
        sa.Column("work_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("stored_name", sa.String(length=500), nullable=False),
        sa.Column("storage_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_email", sa.String(length=320), nullable=True),
        sa.Column("uploaded_by_name", sa.String(length=500), nullable=True),
        sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_session_id"], ["calculation_sessions.id"]),
        sa.ForeignKeyConstraint(["synced_quote_id"], ["eworks_quotes.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attachment_id"),
    )
    op.create_index("ix_quote_work_attachments_attachment_id", "quote_work_attachments", ["attachment_id"])
    op.create_index("ix_quote_work_attachments_quote_ref", "quote_work_attachments", ["quote_ref"])
    op.create_index("ix_quote_work_attachments_eworks_quote_id", "quote_work_attachments", ["eworks_quote_id"])
    op.create_index("ix_quote_work_attachments_synced_quote_id", "quote_work_attachments", ["synced_quote_id"])
    op.create_index(
        "ix_quote_work_attachments_quote_work",
        "quote_work_attachments",
        ["eworks_quote_id", "quote_ref", "work_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_quote_work_attachments_quote_work", table_name="quote_work_attachments")
    op.drop_index("ix_quote_work_attachments_synced_quote_id", table_name="quote_work_attachments")
    op.drop_index("ix_quote_work_attachments_eworks_quote_id", table_name="quote_work_attachments")
    op.drop_index("ix_quote_work_attachments_quote_ref", table_name="quote_work_attachments")
    op.drop_index("ix_quote_work_attachments_attachment_id", table_name="quote_work_attachments")
    op.drop_table("quote_work_attachments")
