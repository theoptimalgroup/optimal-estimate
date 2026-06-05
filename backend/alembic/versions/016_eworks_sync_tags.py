"""Add tags JSON columns to eworks_quotes and eworks_jobs.

Revision ID: 016
Revises: 015
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eworks_quotes", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("eworks_jobs", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("eworks_jobs", "tags")
    op.drop_column("eworks_quotes", "tags")
