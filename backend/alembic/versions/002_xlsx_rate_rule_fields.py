"""Add XLSX formula fields to rate_rules.

Revision ID: 002
Revises: 001
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rate_rules", sa.Column("client_fee_pct", sa.Numeric(8, 4), nullable=False, server_default="0"))
    op.add_column("rate_rules", sa.Column("hourly_overhead_pct", sa.Numeric(8, 4), nullable=False, server_default="0.30"))
    op.add_column("rate_rules", sa.Column("daily_overhead_pct", sa.Numeric(8, 4), nullable=False, server_default="0.20"))
    op.add_column(
        "rate_rules",
        sa.Column("daily_overhead_long_job_pct", sa.Numeric(8, 4), nullable=False, server_default="0.15"),
    )
    op.add_column("rate_rules", sa.Column("direct_hourly_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("rate_rules", sa.Column("direct_daily_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("rate_rules", sa.Column("labourer_hourly_cost", sa.Numeric(12, 2), nullable=False, server_default="18.75"))
    op.add_column("rate_rules", sa.Column("labourer_daily_cost", sa.Numeric(12, 2), nullable=False, server_default="150"))
    op.add_column(
        "rate_rules",
        sa.Column("material_charge_denominator", sa.Numeric(8, 4), nullable=False, server_default="0.20"),
    )
    op.add_column(
        "rate_rules",
        sa.Column("parking_charge_denominator", sa.Numeric(8, 4), nullable=False, server_default="0.20"),
    )
    op.add_column(
        "rate_rules",
        sa.Column("congestion_charge_denominator", sa.Numeric(8, 4), nullable=False, server_default="0.20"),
    )
    op.add_column("rate_rules", sa.Column("mround_increment", sa.Numeric(8, 2), nullable=False, server_default="5"))
    op.add_column("rate_rules", sa.Column("oj_uplift_pct", sa.Numeric(8, 2), nullable=False, server_default="10"))
    op.add_column("rate_rules", sa.Column("nhs_overhead_uplift_pct", sa.Numeric(8, 2), nullable=False, server_default="15"))
    op.add_column("rate_rules", sa.Column("eaf_flat_fee", sa.Numeric(12, 2), nullable=False, server_default="1"))
    op.add_column("rate_rules", sa.Column("internal_notes_template", sa.Text(), nullable=True))
    op.add_column(
        "rate_rules",
        sa.Column("formula_source", sa.String(20), nullable=False, server_default="simplified"),
    )
    op.add_column("rate_rules", sa.Column("xlsx_client_name", sa.String(255), nullable=True))
    op.add_column("rate_rules", sa.Column("xlsx_trade_name", sa.String(255), nullable=True))


def downgrade() -> None:
    columns = [
        "client_fee_pct",
        "hourly_overhead_pct",
        "daily_overhead_pct",
        "daily_overhead_long_job_pct",
        "direct_hourly_cost",
        "direct_daily_cost",
        "labourer_hourly_cost",
        "labourer_daily_cost",
        "material_charge_denominator",
        "parking_charge_denominator",
        "congestion_charge_denominator",
        "mround_increment",
        "oj_uplift_pct",
        "nhs_overhead_uplift_pct",
        "eaf_flat_fee",
        "internal_notes_template",
        "formula_source",
        "xlsx_client_name",
        "xlsx_trade_name",
    ]
    for column in columns:
        op.drop_column("rate_rules", column)
