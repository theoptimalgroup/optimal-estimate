"""Add idempotency_key to calculation_sessions.

Revision ID: 007
Revises: 006
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calculation_sessions", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.create_index(
        "ix_calculation_sessions_idempotency_key",
        "calculation_sessions",
        ["idempotency_key"],
        unique=True,
    )
    op.execute(
        """
        UPDATE calculation_sessions cs
        SET idempotency_key = sub.computed_key
        FROM (
            SELECT id,
                   'eworks.session.' || source || '.' ||
                   (step1_snapshot->>'quote_number') || '.' ||
                   (step1_snapshot->>'job_number') AS computed_key,
                   ROW_NUMBER() OVER (
                       PARTITION BY source,
                                    step1_snapshot->>'quote_number',
                                    step1_snapshot->>'job_number'
                       ORDER BY updated_at DESC NULLS LAST, created_at DESC
                   ) AS rn
            FROM calculation_sessions
            WHERE step1_snapshot->>'quote_number' IS NOT NULL
              AND step1_snapshot->>'job_number' IS NOT NULL
        ) sub
        WHERE cs.id = sub.id
          AND sub.rn = 1
          AND cs.idempotency_key IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_sessions_idempotency_key", table_name="calculation_sessions")
    op.drop_column("calculation_sessions", "idempotency_key")
