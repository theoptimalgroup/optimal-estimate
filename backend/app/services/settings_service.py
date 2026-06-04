from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.product import Product
from app.models.product import Product
from app.models.rate_rule import RateRule
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.schemas.settings import (
    AppSettingsRead,
    AuthSettingsRead,
    DashboardSettingsRead,
    DatabaseSettingsRead,
    EworksAcceptanceSyncSettingsRead,
    EworksSettingsRead,
    PdfSettingsRead,
    SecuritySettingsRead,
    SettingsCountsRead,
    SettingsRead,
    SettingsStatusRead,
    StorageSettingsRead,
)

APP_VERSION = "1.0.0"
REDACTED = "***REDACTED***"


def _storage_provider(settings: Settings) -> str:
    backend = (settings.storage_backend or "").lower()
    if backend in {"local", "azure_blob"}:
        return backend
    if backend:
        return "unknown"
    return "unknown"


def _auth_provider(settings: Settings) -> str:
    return settings.auth_provider


def get_safe_settings(settings: Settings) -> SettingsRead:
    storage_backend = _storage_provider(settings)
    azure_blob_configured = bool(
        settings.azure_storage_account_name
        or settings.azure_storage_connection_string
        or settings.azure_storage_use_managed_identity
    )

    return SettingsRead(
        app=AppSettingsRead(
            environment=settings.environment,
            debug=settings.is_development,
            version=APP_VERSION,
            api_prefix=settings.api_v1_prefix,
            formula_version=settings.formula_version,
            template_version=settings.template_version,
        ),
        auth=AuthSettingsRead(
            dev_auth_enabled=settings.dev_auth_enabled,
            dev_auth_email=settings.dev_user_email,
            dev_auth_auto_create_user=settings.dev_auth_auto_create_user,
            azure_enabled=settings.is_azure_auth,
            auth_provider=_auth_provider(settings),
        ),
        eworks=EworksSettingsRead(
            base_url_configured=bool(settings.eworks_base_url),
            api_key_configured=bool(settings.eworks_api_key),
            license_key_configured=False,
            api_enabled=settings.eworks_api_enabled,
            acceptance_sync=EworksAcceptanceSyncSettingsRead(
                enabled=settings.eworks_acceptance_sync_enabled,
                mode=settings.eworks_acceptance_sync_mode,
                custom_field_id=settings.eworks_acceptance_custom_field_id,
                custom_field_key=settings.eworks_acceptance_custom_field_key,
                custom_field_configured=bool(settings.eworks_acceptance_custom_field_key),
            ),
        ),
        dashboard=DashboardSettingsRead(
            password_configured=bool(settings.dashboard_password),
            password_value=REDACTED if settings.dashboard_password else REDACTED,
        ),
        storage=StorageSettingsRead(
            provider=storage_backend,
            azure_blob_configured=azure_blob_configured,
        ),
        pdf=PdfSettingsRead(
            enabled=True,
            engine="weasyprint",
        ),
        database=DatabaseSettingsRead(
            configured=bool(settings.database_url),
            url=REDACTED,
        ),
        security=SecuritySettingsRead(
            cors_origins_count=len(settings.cors_origin_list),
            allowed_hosts_count=None,
        ),
    )


def _table_count(db: Session, model) -> int:
    try:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)
    except Exception:
        db.rollback()
        return 0


def _safe_scalar(db: Session, query):
    try:
        return db.scalar(query)
    except Exception:
        db.rollback()
        return None


def get_settings_status(db: Session) -> SettingsStatusRead:
    database_reachable = False
    try:
        db.execute(text("SELECT 1"))
        database_reachable = True
    except Exception:
        database_reachable = False

    submitted_sessions = int(
        db.scalar(
            select(func.count()).select_from(CalculationSession).where(CalculationSession.status == "submitted")
        )
        or 0
    )

    last_product_sync_at = _safe_scalar(db, select(func.max(Product.updated_at)))
    latest_audit_log_at = _safe_scalar(db, select(func.max(AuditLog.created_at)))

    counts = SettingsCountsRead(
        users=_table_count(db, User),
        clients=_table_count(db, Client),
        trades=_table_count(db, Trade),
        products=_table_count(db, Product),
        rate_rules=_table_count(db, RateRule),
        submitted_sessions=submitted_sessions,
        audit_logs=_table_count(db, AuditLog),
    )

    return SettingsStatusRead(
        database_reachable=database_reachable,
        counts=counts,
        last_product_sync_at=last_product_sync_at if isinstance(last_product_sync_at, datetime) else None,
        latest_audit_log_at=latest_audit_log_at if isinstance(latest_audit_log_at, datetime) else None,
    )
