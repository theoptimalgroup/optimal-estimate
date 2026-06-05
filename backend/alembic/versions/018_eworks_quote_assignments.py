"""Add eworks_quote_assignments table for manager quote assignments.

Revision ID: 018
Revises: 017
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eworks_quote_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("synced_quote_id", sa.Integer(), sa.ForeignKey("eworks_quotes.id"), nullable=False),
        sa.Column("eworks_quote_id", sa.Integer(), nullable=False),
        sa.Column("quote_ref", sa.String(100), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_user_email", sa.String(320), nullable=True),
        sa.Column("assigned_user_name", sa.String(500), nullable=True),
        sa.Column("assignment_type", sa.String(20), nullable=False),
        sa.Column("assignee_kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="assigned"),
        sa.Column("assignment_token", sa.String(128), nullable=True, unique=True),
        sa.Column("assignment_token_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignment_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignment_token_revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_by_email", sa.String(320), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_eworks_quote_assignments_synced_quote_id",
        "eworks_quote_assignments",
        ["synced_quote_id"],
    )
    op.create_index(
        "ix_eworks_quote_assignments_assigned_user_id",
        "eworks_quote_assignments",
        ["assigned_user_id"],
    )
    op.create_index(
        "ix_eworks_quote_assignments_assigned_user_email",
        "eworks_quote_assignments",
        ["assigned_user_email"],
    )
    op.create_index(
        "ix_eworks_quote_assignments_assignment_token",
        "eworks_quote_assignments",
        ["assignment_token"],
    )
    op.create_index("ix_eworks_quote_assignments_status", "eworks_quote_assignments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_eworks_quote_assignments_status", table_name="eworks_quote_assignments")
    op.drop_index("ix_eworks_quote_assignments_assignment_token", table_name="eworks_quote_assignments")
    op.drop_index("ix_eworks_quote_assignments_assigned_user_email", table_name="eworks_quote_assignments")
    op.drop_index("ix_eworks_quote_assignments_assigned_user_id", table_name="eworks_quote_assignments")
    op.drop_index("ix_eworks_quote_assignments_synced_quote_id", table_name="eworks_quote_assignments")
    op.drop_table("eworks_quote_assignments")
