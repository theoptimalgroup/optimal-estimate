from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


EnvironmentName = Literal["development", "staging", "production"]


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

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
