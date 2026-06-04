from datetime import datetime

from pydantic import BaseModel, Field


class AppSettingsRead(BaseModel):
    environment: str
    debug: bool
    version: str
    api_prefix: str
    formula_version: str
    template_version: str


class AuthSettingsRead(BaseModel):
    dev_auth_enabled: bool
    dev_auth_email: str
    dev_auth_auto_create_user: bool
    azure_enabled: bool = False
    auth_provider: str


class EworksAcceptanceSyncSettingsRead(BaseModel):
    enabled: bool = False
    mode: str = "custom_field"
    custom_field_id: int = 45
    custom_field_key: str = "txtar_45"
    custom_field_configured: bool = True


class EworksSettingsRead(BaseModel):
    base_url_configured: bool
    api_key_configured: bool
    license_key_configured: bool
    api_enabled: bool
    acceptance_sync: EworksAcceptanceSyncSettingsRead = EworksAcceptanceSyncSettingsRead()


class DashboardSettingsRead(BaseModel):
    password_configured: bool
    password_value: str = "***REDACTED***"


class StorageSettingsRead(BaseModel):
    provider: str
    azure_blob_configured: bool


class PdfSettingsRead(BaseModel):
    enabled: bool
    engine: str


class DatabaseSettingsRead(BaseModel):
    configured: bool
    url: str = "***REDACTED***"


class SecuritySettingsRead(BaseModel):
    cors_origins_count: int
    allowed_hosts_count: int | None = None


class SettingsRead(BaseModel):
    app: AppSettingsRead
    auth: AuthSettingsRead
    eworks: EworksSettingsRead
    dashboard: DashboardSettingsRead
    storage: StorageSettingsRead
    pdf: PdfSettingsRead
    database: DatabaseSettingsRead
    security: SecuritySettingsRead


class SettingsCountsRead(BaseModel):
    users: int
    clients: int
    trades: int
    products: int
    rate_rules: int
    submitted_sessions: int
    audit_logs: int


class SettingsStatusRead(BaseModel):
    database_reachable: bool
    counts: SettingsCountsRead
    last_product_sync_at: datetime | None = None
    latest_audit_log_at: datetime | None = None
