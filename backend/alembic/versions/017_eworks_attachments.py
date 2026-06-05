"""Add eworks_attachments table for quote/job attachment metadata sync.

Revision ID: 017
Revises: 016
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eworks_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("eworks_attachment_id", sa.String(100), nullable=True),
        sa.Column("parent_type", sa.String(10), nullable=False),
        sa.Column("parent_eworks_id", sa.Integer(), nullable=False),
        sa.Column("parent_local_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("mime_type", sa.String(200), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_on", sa.String(30), nullable=True),
        sa.Column("uploaded_by", sa.String(200), nullable=True),
        sa.Column("download_endpoint", sa.String(1000), nullable=True),
        sa.Column("local_storage_path", sa.String(1000), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_eworks_attachments_parent",
        "eworks_attachments",
        ["parent_type", "parent_eworks_id"],
    )
    op.create_index(
        "ix_eworks_attachments_eworks_attachment_id",
        "eworks_attachments",
        ["eworks_attachment_id"],
    )
    op.create_index("ix_eworks_attachments_filename", "eworks_attachments", ["filename"])


def downgrade() -> None:
    op.drop_index("ix_eworks_attachments_filename", table_name="eworks_attachments")
    op.drop_index("ix_eworks_attachments_eworks_attachment_id", table_name="eworks_attachments")
    op.drop_index("ix_eworks_attachments_parent", table_name="eworks_attachments")
    op.drop_table("eworks_attachments")
