"""Add frozen product/scope context to quote work attachments.

Revision ID: 030
Revises: 029
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quote_work_attachments", sa.Column("product_id", sa.Integer(), nullable=True))
    op.add_column("quote_work_attachments", sa.Column("product_name", sa.String(length=500), nullable=True))
    op.add_column("quote_work_attachments", sa.Column("is_custom_scope", sa.Boolean(), nullable=True))
    op.add_column("quote_work_attachments", sa.Column("custom_scope_title", sa.String(length=500), nullable=True))
    op.add_column("quote_work_attachments", sa.Column("scope_snapshot", sa.Text(), nullable=True))
    op.add_column("quote_work_attachments", sa.Column("work_block_label", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("quote_work_attachments", "work_block_label")
    op.drop_column("quote_work_attachments", "scope_snapshot")
    op.drop_column("quote_work_attachments", "custom_scope_title")
    op.drop_column("quote_work_attachments", "is_custom_scope")
    op.drop_column("quote_work_attachments", "product_name")
    op.drop_column("quote_work_attachments", "product_id")
