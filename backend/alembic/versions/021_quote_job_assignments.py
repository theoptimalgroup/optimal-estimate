"""Add quote_job_assignments table for manager job award decisions.

Revision ID: 021
Revises: 020
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_job_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quote_ref", sa.String(100), nullable=True),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=True),
        sa.Column("group_key", sa.String(200), nullable=True),
        sa.Column(
            "selected_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_sessions.id"),
            nullable=False,
        ),
        sa.Column("assignee_name", sa.String(500), nullable=False),
        sa.Column("assignee_email", sa.String(320), nullable=True),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("eworks_quote_assignments.id"),
            nullable=True,
        ),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_by_email", sa.String(320), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_quote_job_assignments_quote_ref", "quote_job_assignments", ["quote_ref"])
    op.create_index("ix_quote_job_assignments_eworks_quote_id", "quote_job_assignments", ["eworks_quote_id"])
    op.create_index(
        "ix_quote_job_assignments_selected_session_id",
        "quote_job_assignments",
        ["selected_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quote_job_assignments_selected_session_id", table_name="quote_job_assignments")
    op.drop_index("ix_quote_job_assignments_eworks_quote_id", table_name="quote_job_assignments")
    op.drop_index("ix_quote_job_assignments_quote_ref", table_name="quote_job_assignments")
    op.drop_table("quote_job_assignments")
