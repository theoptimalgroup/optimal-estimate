"""Extend job appointments and add quote sales appointments table.

Revision ID: 027
Revises: 026
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eworks_job_appointments",
        sa.Column("is_sales_appointment", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "eworks_job_appointments",
        sa.Column("user_mobile", sa.String(100), nullable=True),
    )
    op.add_column(
        "eworks_job_appointments",
        sa.Column("user_telephone", sa.String(100), nullable=True),
    )
    op.add_column(
        "eworks_job_appointments",
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
    )

    op.create_table(
        "eworks_quote_appointments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("quote_ref", sa.String(100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_name", sa.String(500), nullable=True),
        sa.Column("user_email", sa.String(320), nullable=True),
        sa.Column("user_mobile", sa.String(100), nullable=True),
        sa.Column("user_telephone", sa.String(100), nullable=True),
        sa.Column("appointment_type", sa.String(200), nullable=True),
        sa.Column("status", sa.String(200), nullable=True),
        sa.Column("is_sales_appointment", sa.Boolean(), nullable=True),
        sa.Column("start_at", sa.String(50), nullable=True),
        sa.Column("end_at", sa.String(50), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("raw_safe_snapshot", sa.JSON(), nullable=True),
        sa.Column("dedupe_key", sa.String(300), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["eworks_quote_id"],
            ["eworks_quotes.eworks_quote_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "eworks_quote_id",
            "dedupe_key",
            name="uq_eworks_quote_appointments_quote_dedupe",
        ),
    )
    op.create_index(
        "ix_eworks_quote_appointments_eworks_quote_id",
        "eworks_quote_appointments",
        ["eworks_quote_id"],
    )
    op.create_index(
        "ix_eworks_quote_appointments_user_email",
        "eworks_quote_appointments",
        ["user_email"],
    )


def downgrade() -> None:
    op.drop_index("ix_eworks_quote_appointments_user_email", table_name="eworks_quote_appointments")
    op.drop_index("ix_eworks_quote_appointments_eworks_quote_id", table_name="eworks_quote_appointments")
    op.drop_table("eworks_quote_appointments")

    op.drop_column("eworks_job_appointments", "duration_minutes")
    op.drop_column("eworks_job_appointments", "user_telephone")
    op.drop_column("eworks_job_appointments", "user_mobile")
    op.drop_column("eworks_job_appointments", "is_sales_appointment")
