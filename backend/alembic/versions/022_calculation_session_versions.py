"""Add estimate revision versioning.

Revision ID: 022
Revises: 021
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calculation_sessions",
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "calculation_sessions",
        sa.Column("revision_in_progress", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("calculation_sessions", sa.Column("active_revision_reason", sa.Text(), nullable=True))
    op.add_column("calculation_sessions", sa.Column("last_revised_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "calculation_sessions",
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("calculation_sessions", sa.Column("submitted_by_name", sa.String(500), nullable=True))
    op.add_column("calculation_sessions", sa.Column("submitted_by_email", sa.String(320), nullable=True))

    op.create_table(
        "calculation_session_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("step1_snapshot", postgresql.JSON(), nullable=False),
        sa.Column("step2_snapshot", postgresql.JSON(), nullable=True),
        sa.Column("calculation_result", postgresql.JSON(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitted_by_name", sa.String(500), nullable=True),
        sa.Column("submitted_by_email", sa.String(320), nullable=True),
        sa.Column("revision_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="submitted"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "version_number", name="uq_calculation_session_versions_session_version"),
    )
    op.create_index(
        "ix_calculation_session_versions_session_id",
        "calculation_session_versions",
        ["session_id"],
    )
    op.create_index(
        "ix_calculation_session_versions_is_current",
        "calculation_session_versions",
        ["is_current"],
    )

    op.execute(
        """
        INSERT INTO calculation_session_versions (
            id, session_id, version_number, step1_snapshot, step2_snapshot,
            calculation_result, submitted_at, status, is_current, revision_reason
        )
        SELECT
            gen_random_uuid(),
            cs.id,
            1,
            cs.step1_snapshot,
            cs.step2_snapshot,
            CASE
                WHEN cs.ui_state IS NOT NULL AND cs.ui_state ? 'last_result'
                THEN cs.ui_state -> 'last_result'
                ELSE NULL
            END,
            cs.submitted_at,
            'submitted',
            TRUE,
            NULL
        FROM calculation_sessions cs
        WHERE cs.status = 'submitted' AND cs.submitted_at IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE calculation_sessions
        SET locked = TRUE,
            current_version_number = 1
        WHERE status = 'submitted' AND submitted_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_session_versions_is_current", table_name="calculation_session_versions")
    op.drop_index("ix_calculation_session_versions_session_id", table_name="calculation_session_versions")
    op.drop_table("calculation_session_versions")
    op.drop_column("calculation_sessions", "submitted_by_email")
    op.drop_column("calculation_sessions", "submitted_by_name")
    op.drop_column("calculation_sessions", "submitted_by_user_id")
    op.drop_column("calculation_sessions", "last_revised_at")
    op.drop_column("calculation_sessions", "active_revision_reason")
    op.drop_column("calculation_sessions", "revision_in_progress")
    op.drop_column("calculation_sessions", "current_version_number")
    op.drop_column("calculation_sessions", "locked")
