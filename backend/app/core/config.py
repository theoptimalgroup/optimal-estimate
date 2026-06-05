from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


EnvironmentName = Literal["development", "staging", "production"]


AuthProviderName = Literal["dev", "azure"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "postgresql+psycopg2://estimate:estimate_dev@localhost:5432/estimate_tool"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:3000"
    environment: EnvironmentName = "development"
    api_v1_prefix: str = "/api/v1"
    formula_version: str = "1.0.0"
    xlsx_formula_version: str = "xlsx-master-helper-1.7"
    template_version: str = "1.0.0"
    log_level: str = "INFO"
    eworks_link_secret: str | None = None
    eworks_link_sig_required: bool = False
    eworks_session_expire_minutes: int = 480
    eworks_attachment_path: str = "./storage/eworks-attachments"
    dashboard_password: str = "optimal-dev"

    # Auth provider: dev (local) or azure (Microsoft Entra ID)
    auth_provider: AuthProviderName = "dev"

    # Dev auth (internal users; used when auth_provider=dev)
    dev_auth_enabled: bool = False
    dev_user_id: str = "dev-user-1"
    dev_user_email: str = "admin@optimal.example"
    dev_user_name: str = "Admin User"
    dev_user_role: str = "admin"
    dev_user_is_active: bool = True
    dev_auth_auto_create_user: bool = False

    # Microsoft Entra ID (Azure AD) — used when auth_provider=azure
    azure_tenant_id: str | None = None
    azure_api_client_id: str | None = None
    azure_issuer: str | None = None
    azure_jwks_url: str | None = None

    # eWorks REST API (Customer lookup on link open)
    eworks_base_url: str | None = None
    eworks_api_key: str | None = None
    eworks_api_enabled: bool = False
    eworks_api_timeout_seconds: float = 10.0
    eworks_sync_attachments_enabled: bool = False
    eworks_sync_attachment_files_enabled: bool = False

    # eWorks acceptance sync (client quote acceptance → eWorks custom field)
    eworks_acceptance_sync_enabled: bool = False
    eworks_acceptance_sync_mode: str = "custom_field"
    eworks_acceptance_custom_field_id: int = 45
    eworks_acceptance_custom_field_key: str = "txtar_45"

    # Storage
    storage_backend: str = "local"  # local | azure_blob
    pdf_storage_path: str = "./storage/pdfs"
    azure_storage_account_name: str | None = None
    azure_storage_container_name: str = "quote-documents"
    azure_storage_connection_string: str | None = None
    azure_storage_use_managed_identity: bool = False
    azure_storage_blob_prefix: str = "quotes"

    # Azure Key Vault (optional programmatic loading; App Service Key Vault references also work via env vars)
    key_vault_url: str | None = None
    use_key_vault: bool = False
    key_vault_secret_key_name: str = "SECRET-KEY"
    key_vault_database_url_name: str = "DATABASE-URL"

    # Application Insights
    applicationinsights_connection_string: str | None = None
    enable_application_insights: bool = False

    # App Service
    web_concurrency: int = Field(default=2, ge=1, le=16)
    port: int = 8000
    run_seed: bool = False
    allow_production_seed: bool = False
    frontend_url: str | None = None
    azure_storage_managed_identity_client_id: str | None = None

    # Azure OpenAI — scope rewording
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_use_managed_identity: bool = False
    scope_reword_enabled: bool = False

    @property
    def scope_reword_configured(self) -> bool:
        if not self.azure_openai_endpoint or not self.azure_openai_deployment:
            return False
        if self.azure_openai_use_managed_identity:
            return True
        return bool(self.azure_openai_api_key)

    @property
    def effective_scope_reword_enabled(self) -> bool:
        if not self.scope_reword_enabled:
            return False
        return self.scope_reword_configured

    @property
    def effective_azure_issuer(self) -> str | None:
        if self.azure_issuer:
            return self.azure_issuer.rstrip("/")
        if self.azure_tenant_id:
            return f"https://login.microsoftonline.com/{self.azure_tenant_id}/v2.0"
        return None

    @property
    def effective_azure_jwks_url(self) -> str | None:
        if self.azure_jwks_url:
            return self.azure_jwks_url
        if self.azure_tenant_id:
            return f"https://login.microsoftonline.com/{self.azure_tenant_id}/discovery/v2.0/keys"
        return None

    @property
    def is_azure_auth(self) -> bool:
        return self.auth_provider == "azure"

    @property
    def is_dev_auth(self) -> bool:
        return self.auth_provider == "dev"

    @field_validator("auth_provider", mode="before")
    @classmethod
    def normalize_auth_provider(cls, value: str) -> str:
        normalized = (value or "dev").lower()
        if normalized not in {"dev", "azure"}:
            return "dev"
        return normalized

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        normalized = (value or "development").lower()
        if normalized not in {"development", "staging", "production"}:
            return "development"
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        if self.frontend_url and self.environment in {"staging", "production"}:
            return [self.frontend_url.rstrip("/")]
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_run_seed(self) -> bool:
        if self.is_production and self.run_seed and not self.allow_production_seed:
            return False
        return self.run_seed

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def should_enable_application_insights(self) -> bool:
        return self.enable_application_insights and bool(self.applicationinsights_connection_string)

    @model_validator(mode="after")
    def apply_key_vault_secrets(self) -> "Settings":
        if not self.use_key_vault or not self.key_vault_url:
            return self
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError:
            return self

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=self.key_vault_url, credential=credential)
        updates: dict[str, str] = {}
        try:
            updates["secret_key"] = client.get_secret(self.key_vault_secret_key_name).value
        except Exception:
            pass
        try:
            updates["database_url"] = client.get_secret(self.key_vault_database_url_name).value
        except Exception:
            pass
        return self.model_copy(update=updates)

    @model_validator(mode="after")
    def validate_deployed_environment(self) -> "Settings":
        if self.environment not in {"staging", "production"}:
            return self

        if self.eworks_link_sig_required and not (self.eworks_link_secret or self.secret_key):
            raise ValueError("EWORKS_LINK_SECRET or SECRET_KEY must be set when signature is required")

        origins = self.cors_origin_list
        if not origins:
            raise ValueError("CORS_ORIGINS or FRONTEND_URL must be set for staging/production")

        for origin in origins:
            if origin == "*":
                raise ValueError("Wildcard CORS is not allowed in staging/production")
            if self.is_production and ("localhost" in origin or "127.0.0.1" in origin):
                raise ValueError("localhost origins are not allowed in production CORS")

        if self.storage_backend.lower() == "azure_blob":
            if not self.azure_storage_account_name and not self.azure_storage_connection_string:
                raise ValueError("Azure Blob Storage requires AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_CONNECTION_STRING")
            if not self.azure_storage_connection_string and not self.azure_storage_use_managed_identity:
                raise ValueError("Azure Blob Storage in staging/production requires managed identity or a connection string")

        if self.eworks_api_enabled:
            if not self.eworks_base_url or not self.eworks_api_key:
                raise ValueError("EWORKS_API_ENABLED requires EWORKS_BASE_URL and EWORKS_API_KEY")

        if self.auth_provider == "azure":
            if not self.azure_tenant_id or not self.azure_api_client_id:
                raise ValueError("AUTH_PROVIDER=azure requires AZURE_TENANT_ID and AZURE_API_CLIENT_ID")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
