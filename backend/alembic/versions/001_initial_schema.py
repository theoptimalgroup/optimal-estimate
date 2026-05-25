"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("billing_email", sa.String(255)),
        sa.Column("default_vat_rate", sa.Numeric(5, 2), server_default="20.00"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "rate_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id")),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trades.id")),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(12, 2)),
        sa.Column("half_day_rate", sa.Numeric(12, 2)),
        sa.Column("day_rate", sa.Numeric(12, 2)),
        sa.Column("minimum_hours", sa.Numeric(8, 2)),
        sa.Column("minimum_charge", sa.Numeric(12, 2)),
        sa.Column("material_markup_type", sa.String(50), server_default="percentage"),
        sa.Column("material_markup_value", sa.Numeric(8, 2), server_default="0"),
        sa.Column("vat_rate", sa.Numeric(5, 2), server_default="20.00"),
        sa.Column("approval_threshold", sa.Numeric(12, 2)),
        sa.Column("minimum_margin_percentage", sa.Numeric(5, 2)),
        sa.Column("rounding_rule", sa.String(100)),
        sa.Column("active_from", sa.Date(), nullable=False),
        sa.Column("active_to", sa.Date()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_number", sa.String(100), unique=True, nullable=False),
        sa.Column("external_eworks_job_id", sa.String(100)),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id")),
        sa.Column("property_address", sa.Text(), nullable=False),
        sa.Column("property_manager_name", sa.String(255)),
        sa.Column("property_manager_email", sa.String(255)),
        sa.Column("property_manager_phone", sa.String(100)),
        sa.Column("tenant_name", sa.String(255)),
        sa.Column("tenant_phone", sa.String(100)),
        sa.Column("access_notes", sa.Text()),
        sa.Column("original_job_description", sa.Text()),
        sa.Column("engineer_name", sa.String(255)),
        sa.Column("date_visited", sa.Date()),
        sa.Column("travel_time_minutes", sa.Integer(), server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "job_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE")),
        sa.Column("findings", sa.Text(), nullable=False),
        sa.Column("problem_summary", sa.Text()),
        sa.Column("access_confirmed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("tenant_call_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_number", sa.String(100), unique=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE")),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("rule_version", sa.String(100)),
        sa.Column("formula_version", sa.String(100)),
        sa.Column("template_version", sa.String(100)),
        sa.Column("subtotal", sa.Numeric(12, 2), server_default="0"),
        sa.Column("vat_rate", sa.Numeric(5, 2), server_default="20.00"),
        sa.Column("vat_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("final_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("margin_total", sa.Numeric(12, 2)),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("client_notes", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "quote_scope_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("client_visible", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("internal_only", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "quote_labour",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trades.id")),
        sa.Column("skill_required", sa.String(255)),
        sa.Column("best_engineer", sa.String(255)),
        sa.Column("labour_type", sa.String(50), nullable=False),
        sa.Column("number_of_engineers", sa.Integer(), nullable=False),
        sa.Column("hours_on_site", sa.Numeric(8, 2)),
        sa.Column("days_on_site", sa.Numeric(8, 2)),
        sa.Column("rate_used", sa.Numeric(12, 2)),
        sa.Column("labour_total", sa.Numeric(12, 2)),
        sa.Column("manual_override", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("manual_rate", sa.Numeric(12, 2)),
        sa.Column("override_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "quote_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("material_name", sa.String(255), nullable=False),
        sa.Column("supplier_name", sa.String(255)),
        sa.Column("supplier_link", sa.Text()),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_cost", sa.Numeric(12, 2), server_default="0"),
        sa.Column("markup_type", sa.String(50), server_default="percentage"),
        sa.Column("markup_value", sa.Numeric(8, 2), server_default="0"),
        sa.Column("base_cost", sa.Numeric(12, 2)),
        sa.Column("markup_total", sa.Numeric(12, 2)),
        sa.Column("sell_total", sa.Numeric(12, 2)),
        sa.Column("client_visible", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "quote_charges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("parking_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("parking_type", sa.String(50)),
        sa.Column("parking_rate_per_hour", sa.Numeric(12, 2)),
        sa.Column("parking_hours", sa.Numeric(8, 2)),
        sa.Column("parking_fixed_amount", sa.Numeric(12, 2)),
        sa.Column("parking_total", sa.Numeric(12, 2), server_default="0"),
        sa.Column("congestion_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("congestion_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("ulez_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("ulez_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("waste_disposal_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("waste_disposal_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("travel_charge", sa.Numeric(12, 2), server_default="0"),
        sa.Column("other_charge", sa.Numeric(12, 2), server_default="0"),
        sa.Column("other_charge_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "calculation_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("rule_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("output_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("calculated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("approval_reason", sa.Text()),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quotes.id", ondelete="CASCADE")),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("template_version", sa.String(100)),
        sa.Column("is_draft", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("old_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB()),
        sa.Column("ip_address", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "integration_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(255), unique=True, nullable=False),
        sa.Column("source_system", sa.String(100)),
        sa.Column("target_system", sa.String(100)),
        sa.Column("entity_type", sa.String(100)),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(50)),
        sa.Column("request_payload", postgresql.JSONB()),
        sa.Column("response_payload", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(255), unique=True, nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB()),
        sa.Column("status_code", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in [
        "idempotency_keys",
        "integration_events",
        "audit_logs",
        "documents",
        "approvals",
        "calculation_snapshots",
        "quote_charges",
        "quote_materials",
        "quote_labour",
        "quote_scope_items",
        "quotes",
        "job_findings",
        "jobs",
        "rate_rules",
        "trades",
        "clients",
        "users",
    ]:
        op.drop_table(table)
