"""Add eworks_job_appointments and job assignee snapshot columns.

Revision ID: 024
Revises: 023
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eworks_job_appointments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("eworks_job_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("job_ref", sa.String(100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_name", sa.String(500), nullable=True),
        sa.Column("user_email", sa.String(320), nullable=True),
        sa.Column("appointment_type", sa.String(200), nullable=True),
        sa.Column("status", sa.String(200), nullable=True),
        sa.Column("start_at", sa.String(50), nullable=True),
        sa.Column("end_at", sa.String(50), nullable=True),
        sa.Column("raw_safe_snapshot", sa.JSON(), nullable=True),
        sa.Column("dedupe_key", sa.String(300), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["eworks_job_id"], ["eworks_jobs.eworks_job_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("eworks_job_id", "dedupe_key", name="uq_eworks_job_appointments_job_dedupe"),
    )
    op.create_index(
        "ix_eworks_job_appointments_eworks_job_id",
        "eworks_job_appointments",
        ["eworks_job_id"],
    )
    op.create_index(
        "ix_eworks_job_appointments_user_email",
        "eworks_job_appointments",
        ["user_email"],
    )
    op.create_index(
        "ix_eworks_job_appointments_user_name",
        "eworks_job_appointments",
        ["user_name"],
    )

    op.add_column("eworks_jobs", sa.Column("assigned_user_name", sa.String(500), nullable=True))
    op.add_column("eworks_jobs", sa.Column("assigned_user_email", sa.String(320), nullable=True))
    op.add_column("eworks_jobs", sa.Column("assigned_user_id", sa.Integer(), nullable=True))
    op.add_column("eworks_jobs", sa.Column("next_appointment_at", sa.String(50), nullable=True))
    op.add_column("eworks_jobs", sa.Column("active_appointment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_eworks_jobs_active_appointment_id",
        "eworks_jobs",
        "eworks_job_appointments",
        ["active_appointment_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_eworks_jobs_active_appointment_id", "eworks_jobs", type_="foreignkey")
    op.drop_column("eworks_jobs", "active_appointment_id")
    op.drop_column("eworks_jobs", "next_appointment_at")
    op.drop_column("eworks_jobs", "assigned_user_id")
    op.drop_column("eworks_jobs", "assigned_user_email")
    op.drop_column("eworks_jobs", "assigned_user_name")

    op.drop_index("ix_eworks_job_appointments_user_name", table_name="eworks_job_appointments")
    op.drop_index("ix_eworks_job_appointments_user_email", table_name="eworks_job_appointments")
    op.drop_index("ix_eworks_job_appointments_eworks_job_id", table_name="eworks_job_appointments")
    op.drop_table("eworks_job_appointments")
