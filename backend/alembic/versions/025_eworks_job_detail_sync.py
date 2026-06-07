"""Add eWorks job detail sync columns for appointment extraction.

Revision ID: 025
Revises: 024
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eworks_jobs", sa.Column("total_appointments", sa.Integer(), nullable=True))
    op.add_column("eworks_jobs", sa.Column("completed_appointments", sa.Integer(), nullable=True))
    op.add_column("eworks_jobs", sa.Column("total_appointment_time", sa.String(100), nullable=True))
    op.add_column("eworks_jobs", sa.Column("total_appointment_cost", sa.Numeric(14, 2), nullable=True))
    op.add_column("eworks_jobs", sa.Column("raw_detail_payload", sa.JSON(), nullable=True))
    op.add_column("eworks_jobs", sa.Column("detail_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("eworks_jobs", "detail_synced_at")
    op.drop_column("eworks_jobs", "raw_detail_payload")
    op.drop_column("eworks_jobs", "total_appointment_cost")
    op.drop_column("eworks_jobs", "total_appointment_time")
    op.drop_column("eworks_jobs", "completed_appointments")
    op.drop_column("eworks_jobs", "total_appointments")
