"""Add eworks_sync_locks table for distributed sync coordination.

Revision ID: 026
Revises: 025
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eworks_sync_locks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sync_type", sa.String(32), nullable=False),
        sa.Column("locked_by", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("sync_type", name="uq_eworks_sync_locks_sync_type"),
    )
    op.create_index("ix_eworks_sync_locks_status", "eworks_sync_locks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_eworks_sync_locks_status", table_name="eworks_sync_locks")
    op.drop_table("eworks_sync_locks")
