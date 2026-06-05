"""Add eWorks sync tables: eworks_quotes, eworks_jobs, eworks_sync_runs.

Revision ID: 015
Revises: 014
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # eworks_quotes
    op.create_table(
        "eworks_quotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("eworks_quote_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("quote_ref", sa.String(100), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(500), nullable=True),
        sa.Column("customer_contact_id", sa.Integer(), nullable=True),
        sa.Column("customer_site_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("quote_type_id", sa.Integer(), nullable=True),
        sa.Column("quote_source_id", sa.Integer(), nullable=True),
        sa.Column("quote_date", sa.String(30), nullable=True),
        sa.Column("expiry_date", sa.String(30), nullable=True),
        sa.Column("status", sa.String(100), nullable=True),
        sa.Column("status_name", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("customer_notes", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("customer_ref", sa.String(200), nullable=True),
        sa.Column("po_ref", sa.String(200), nullable=True),
        sa.Column("wo_ref", sa.String(200), nullable=True),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=True),
        sa.Column("vat", sa.Numeric(14, 2), nullable=True),
        sa.Column("total", sa.Numeric(14, 2), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_eworks_quotes_eworks_quote_id", "eworks_quotes", ["eworks_quote_id"])
    op.create_index("ix_eworks_quotes_quote_ref", "eworks_quotes", ["quote_ref"])
    op.create_index("ix_eworks_quotes_customer_id", "eworks_quotes", ["customer_id"])
    op.create_index("ix_eworks_quotes_status", "eworks_quotes", ["status"])
    op.create_index("ix_eworks_quotes_synced_at", "eworks_quotes", ["synced_at"])

    # eworks_jobs
    op.create_table(
        "eworks_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("eworks_job_id", sa.Integer(), unique=True, nullable=False),
        sa.Column("job_ref", sa.String(100), nullable=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(500), nullable=True),
        sa.Column("status", sa.String(100), nullable=True),
        sa.Column("status_name", sa.String(200), nullable=True),
        sa.Column("job_date", sa.String(30), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=True),
        sa.Column("vat", sa.Numeric(14, 2), nullable=True),
        sa.Column("total", sa.Numeric(14, 2), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_eworks_jobs_eworks_job_id", "eworks_jobs", ["eworks_job_id"])
    op.create_index("ix_eworks_jobs_job_ref", "eworks_jobs", ["job_ref"])
    op.create_index("ix_eworks_jobs_customer_id", "eworks_jobs", ["customer_id"])
    op.create_index("ix_eworks_jobs_eworks_quote_id", "eworks_jobs", ["eworks_quote_id"])
    op.create_index("ix_eworks_jobs_status", "eworks_jobs", ["status"])
    op.create_index("ix_eworks_jobs_synced_at", "eworks_jobs", ["synced_at"])

    # eworks_sync_runs
    op.create_table(
        "eworks_sync_runs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("sync_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_eworks_sync_runs_sync_type", "eworks_sync_runs", ["sync_type"])
    op.create_index("ix_eworks_sync_runs_started_at", "eworks_sync_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_eworks_sync_runs_started_at", table_name="eworks_sync_runs")
    op.drop_index("ix_eworks_sync_runs_sync_type", table_name="eworks_sync_runs")
    op.drop_table("eworks_sync_runs")

    op.drop_index("ix_eworks_jobs_synced_at", table_name="eworks_jobs")
    op.drop_index("ix_eworks_jobs_status", table_name="eworks_jobs")
    op.drop_index("ix_eworks_jobs_eworks_quote_id", table_name="eworks_jobs")
    op.drop_index("ix_eworks_jobs_customer_id", table_name="eworks_jobs")
    op.drop_index("ix_eworks_jobs_job_ref", table_name="eworks_jobs")
    op.drop_index("ix_eworks_jobs_eworks_job_id", table_name="eworks_jobs")
    op.drop_table("eworks_jobs")

    op.drop_index("ix_eworks_quotes_synced_at", table_name="eworks_quotes")
    op.drop_index("ix_eworks_quotes_status", table_name="eworks_quotes")
    op.drop_index("ix_eworks_quotes_customer_id", table_name="eworks_quotes")
    op.drop_index("ix_eworks_quotes_quote_ref", table_name="eworks_quotes")
    op.drop_index("ix_eworks_quotes_eworks_quote_id", table_name="eworks_quotes")
    op.drop_table("eworks_quotes")
