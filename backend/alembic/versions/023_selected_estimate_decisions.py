"""Add selected_estimate_decisions table and migrate quote_job_assignments rows.

Revision ID: 023
Revises: 022
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "selected_estimate_decisions",
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
        sa.Column(
            "selected_assignment_id",
            sa.Integer(),
            sa.ForeignKey("eworks_quote_assignments.id"),
            nullable=True,
        ),
        sa.Column("selected_assignee_name", sa.String(500), nullable=False),
        sa.Column("selected_assignee_email", sa.String(320), nullable=True),
        sa.Column("selected_assignee_type", sa.String(50), nullable=True),
        sa.Column("final_total", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "selected_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("selected_by_email", sa.String(320), nullable=True),
        sa.Column("selected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_selected_estimate_decisions_quote_ref",
        "selected_estimate_decisions",
        ["quote_ref"],
    )
    op.create_index(
        "ix_selected_estimate_decisions_eworks_quote_id",
        "selected_estimate_decisions",
        ["eworks_quote_id"],
    )
    op.create_index(
        "ix_selected_estimate_decisions_selected_session_id",
        "selected_estimate_decisions",
        ["selected_session_id"],
    )

    op.execute(
        """
        INSERT INTO selected_estimate_decisions (
            quote_ref,
            eworks_quote_id,
            group_key,
            selected_session_id,
            selected_assignment_id,
            selected_assignee_name,
            selected_assignee_email,
            selected_by_user_id,
            selected_by_email,
            selected_at,
            created_at,
            updated_at
        )
        SELECT
            quote_ref,
            eworks_quote_id,
            group_key,
            selected_session_id,
            assignment_id,
            assignee_name,
            assignee_email,
            assigned_by_user_id,
            assigned_by_email,
            assigned_at,
            assigned_at,
            updated_at
        FROM quote_job_assignments
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_selected_estimate_decisions_selected_session_id",
        table_name="selected_estimate_decisions",
    )
    op.drop_index(
        "ix_selected_estimate_decisions_eworks_quote_id",
        table_name="selected_estimate_decisions",
    )
    op.drop_index(
        "ix_selected_estimate_decisions_quote_ref",
        table_name="selected_estimate_decisions",
    )
    op.drop_table("selected_estimate_decisions")
