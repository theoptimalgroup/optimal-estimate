import pytest

from app.core.config import Settings


def test_production_run_seed_disabled_by_default():
    settings = Settings(_env_file=None, environment="production", frontend_url="https://estimate.optimal.example", run_seed=False)
    assert settings.effective_run_seed is False


def test_production_run_seed_requires_explicit_allow_flag():
    settings = Settings(
        _env_file=None,
        environment="production",
        frontend_url="https://estimate.optimal.example",
        run_seed=True,
        allow_production_seed=False,
    )
    assert settings.effective_run_seed is False

    allowed = Settings(
        _env_file=None,
        environment="production",
        frontend_url="https://estimate.optimal.example",
        run_seed=True,
        allow_production_seed=True,
    )
    assert allowed.effective_run_seed is True


def test_production_cors_rejects_localhost():
    with pytest.raises(ValueError, match="localhost origins are not allowed"):
        Settings(
            _env_file=None,
            environment="production",
            cors_origins="http://localhost:3000",
            storage_backend="local",
        )


def test_staging_cors_uses_frontend_url_only():
    settings = Settings(
        _env_file=None,
        environment="staging",
        frontend_url="https://estimate-staging.azurestaticapps.net",
        cors_origins="http://localhost:3000,https://other.example",
        storage_backend="local",
    )
    assert settings.cors_origin_list == ["https://estimate-staging.azurestaticapps.net"]


def test_staging_azure_blob_requires_managed_identity_or_connection_string():
    with pytest.raises(ValueError, match="managed identity or a connection string"):
        Settings(
            _env_file=None,
            environment="staging",
            frontend_url="https://estimate-staging.azurestaticapps.net",
            storage_backend="azure_blob",
            azure_storage_account_name="examplestorage",
            azure_storage_use_managed_identity=False,
        )


def test_staging_azure_blob_accepts_managed_identity():
    settings = Settings(
        _env_file=None,
        environment="staging",
        frontend_url="https://estimate-staging.azurestaticapps.net",
        storage_backend="azure_blob",
        azure_storage_account_name="examplestorage",
        azure_storage_use_managed_identity=True,
    )
    assert settings.storage_backend == "azure_blob"
