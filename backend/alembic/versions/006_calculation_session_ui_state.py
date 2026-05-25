"""Add ui_state to calculation_sessions for resume progress.

Revision ID: 006
Revises: 005
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calculation_sessions", sa.Column("ui_state", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("calculation_sessions", "ui_state")
