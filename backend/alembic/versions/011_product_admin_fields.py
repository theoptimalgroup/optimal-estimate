"""Add is_active and description to products.

Revision ID: 011
Revises: 010
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column("products", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "description")
    op.drop_column("products", "is_active")
