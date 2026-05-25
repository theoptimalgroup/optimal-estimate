"""Add search indexes for clients, trades, and XLSX rate rules.

Revision ID: 004
Revises: 003
Create Date: 2026-05-24
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_clients_name", "clients", ["name"], unique=False)
    op.create_index("ix_trades_name", "trades", ["name"], unique=False)
    op.create_index("ix_rate_rules_client_id", "rate_rules", ["client_id"], unique=False)
    op.create_index("ix_rate_rules_trade_id", "rate_rules", ["trade_id"], unique=False)
    op.create_index("ix_rate_rules_formula_source", "rate_rules", ["formula_source"], unique=False)
    op.create_index("ix_rate_rules_xlsx_client_name", "rate_rules", ["xlsx_client_name"], unique=False)
    op.create_index("ix_rate_rules_xlsx_trade_name", "rate_rules", ["xlsx_trade_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rate_rules_xlsx_trade_name", table_name="rate_rules")
    op.drop_index("ix_rate_rules_xlsx_client_name", table_name="rate_rules")
    op.drop_index("ix_rate_rules_formula_source", table_name="rate_rules")
    op.drop_index("ix_rate_rules_trade_id", table_name="rate_rules")
    op.drop_index("ix_rate_rules_client_id", table_name="rate_rules")
    op.drop_index("ix_trades_name", table_name="trades")
    op.drop_index("ix_clients_name", table_name="clients")
