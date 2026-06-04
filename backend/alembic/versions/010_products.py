"""Add products table for synced eWorks Items.

Revision ID: 010
Revises: 009
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("eworks_item_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=500), nullable=False),
        sa.Column("product_code", sa.String(length=100), nullable=True),
        sa.Column("scope_of_work", sa.Text(), nullable=True),
        sa.Column("cost_price", sa.Numeric(12, 4), server_default="0", nullable=False),
        sa.Column("selling_price", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("margin", sa.Numeric(8, 4), server_default="0", nullable=False),
        sa.Column("tax_rate_id", sa.String(length=50), nullable=True),
        sa.Column("track_stock_level", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("current_stock_level", sa.Numeric(12, 4), server_default="0", nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=100), nullable=True),
        sa.Column("type_id", sa.Integer(), nullable=True),
        sa.Column("eworks_created_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eworks_last_updated_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eworks_item_id"),
    )
    op.create_index("ix_products_eworks_item_id", "products", ["eworks_item_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_products_eworks_item_id", table_name="products")
    op.drop_table("products")
