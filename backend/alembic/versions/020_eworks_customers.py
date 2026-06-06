"""Add eworks_customers table for synced eWorks Customer master data.

Revision ID: 020
Revises: 019
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eworks_customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("eworks_customer_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(length=500), nullable=True),
        sa.Column("full_name", sa.String(length=500), nullable=True),
        sa.Column("company_name", sa.String(length=500), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=100), nullable=True),
        sa.Column("billing_email", sa.String(length=320), nullable=True),
        sa.Column("address_1", sa.String(length=500), nullable=True),
        sa.Column("address_2", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=200), nullable=True),
        sa.Column("county", sa.String(length=200), nullable=True),
        sa.Column("postcode", sa.String(length=50), nullable=True),
        sa.Column("raw_payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eworks_customer_id", name="uq_eworks_customers_eworks_customer_id"),
    )
    op.create_index("ix_eworks_customers_eworks_customer_id", "eworks_customers", ["eworks_customer_id"])
    op.create_index("ix_eworks_customers_customer_name", "eworks_customers", ["customer_name"])
    op.create_index("ix_eworks_customers_synced_at", "eworks_customers", ["synced_at"])


def downgrade() -> None:
    op.drop_index("ix_eworks_customers_synced_at", table_name="eworks_customers")
    op.drop_index("ix_eworks_customers_customer_name", table_name="eworks_customers")
    op.drop_index("ix_eworks_customers_eworks_customer_id", table_name="eworks_customers")
    op.drop_table("eworks_customers")
