"""Add eWorks custom field definitions table.

Revision ID: 028
Revises: 027
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eworks_custom_field_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("eworks_custom_field_id", sa.Integer(), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("field_label", sa.String(length=500), nullable=True),
        sa.Column("field_type", sa.String(length=50), nullable=True),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eworks_custom_field_id"),
        sa.UniqueConstraint("field_key"),
    )
    op.create_index(
        "ix_eworks_custom_field_definitions_field_key",
        "eworks_custom_field_definitions",
        ["field_key"],
        unique=False,
    )
    op.create_index(
        "ix_eworks_custom_field_definitions_synced_at",
        "eworks_custom_field_definitions",
        ["synced_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_eworks_custom_field_definitions_synced_at", table_name="eworks_custom_field_definitions")
    op.drop_index("ix_eworks_custom_field_definitions_field_key", table_name="eworks_custom_field_definitions")
    op.drop_table("eworks_custom_field_definitions")
