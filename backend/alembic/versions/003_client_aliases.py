"""Add client_aliases table for canonical client name resolution.

Revision ID: 003
Revises: 002
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_client_aliases_client_id", "client_aliases", ["client_id"])
    op.create_unique_constraint("uq_client_aliases_alias_name", "client_aliases", ["alias_name"])


def downgrade() -> None:
    op.drop_index("ix_client_aliases_client_id", table_name="client_aliases")
    op.drop_table("client_aliases")
