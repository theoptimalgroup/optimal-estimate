"""Link quote assignments to calculation sessions.

Revision ID: 019
Revises: 018
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eworks_quote_assignments",
        sa.Column(
            "calculation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calculation_sessions.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_eworks_quote_assignments_calculation_session_id",
        "eworks_quote_assignments",
        ["calculation_session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_eworks_quote_assignments_calculation_session_id",
        table_name="eworks_quote_assignments",
    )
    op.drop_column("eworks_quote_assignments", "calculation_session_id")
