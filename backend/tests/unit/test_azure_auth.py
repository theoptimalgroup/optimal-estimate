"""Unit tests for Microsoft Entra ID (Azure) authentication."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.providers.azure import AzureTokenClaims, clear_jwks_cache
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.user import User


def _patch_azure_settings(mock_settings, **overrides):
    defaults = {
        "auth_provider": "azure",
        "is_azure_auth": True,
        "is_dev_auth": False,
        "dev_auth_enabled": False,
        "azure_tenant_id": "test-tenant-id",
        "azure_api_client_id": "test-api-client-id",
        "effective_azure_issuer": "https://login.microsoftonline.com/test-tenant-id/v2.0",
        "effective_azure_jwks_url": "https://login.microsoftonline.com/test-tenant-id/discovery/v2.0/keys",
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(mock_settings, key, value)


def _patch_dev_settings_for_regression(mock_settings, **overrides):
    defaults = {
        "auth_provider": "dev",
        "is_azure_auth": False,
        "is_dev_auth": True,
        "dev_auth_enabled": True,
        "dev_user_id": "dev-user-1",
        "dev_user_email": "dev-only@optimal.example",
        "dev_user_name": "Env User",
        "dev_user_role": "admin",
        "dev_user_is_active": True,
        "dev_auth_auto_create_user": False,
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        setattr(mock_settings, key, value)


@pytest.fixture()
def auth_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def auth_db_client(auth_db):
    def override_get_db():
        try:
            yield auth_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, auth_db
    app.dependency_overrides.clear()


def _seed_user(session, *, email: str, full_name: str, role: UserRole, is_active: bool = True) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid4(),
        email=email,
        full_name=full_name,
        password_hash=get_password_hash("test-password"),
        role=role.value,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@patch("app.auth.dependencies.settings")
@patch("app.auth.dependencies.validate_azure_access_token")
def test_azure_user_mapped_to_db_role(mock_validate, mock_settings, auth_db_client):
    _patch_azure_settings(mock_settings)
    client, session = auth_db_client
    db_user = _seed_user(
        session,
        email="manager@optimal.example",
        full_name="Manager From DB",
        role=UserRole.MANAGER,
    )
    mock_validate.return_value = AzureTokenClaims(
        oid="azure-oid-123",
        email="manager@optimal.example",
        name="Azure Display Name",
        preferred_username="manager@optimal.example",
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(db_user.id)
    assert data["email"] == "manager@optimal.example"
    assert data["name"] == "Manager From DB"
    assert data["role"] == "manager"
    assert data["is_active"] is True
    assert data["auth_provider"] == "azure"


@patch("app.auth.dependencies.settings")
@patch("app.auth.dependencies.validate_azure_access_token")
def test_azure_unknown_user_returns_403(mock_validate, mock_settings, auth_db_client):
    _patch_azure_settings(mock_settings)
    client, _ = auth_db_client
    mock_validate.return_value = AzureTokenClaims(
        oid="azure-oid-unknown",
        email="unknown@optimal.example",
        name="Unknown User",
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "User not registered"


@patch("app.auth.dependencies.settings")
@patch("app.auth.dependencies.validate_azure_access_token")
def test_azure_inactive_user_returns_403(mock_validate, mock_settings, auth_db_client):
    _patch_azure_settings(mock_settings)
    client, session = auth_db_client
    _seed_user(
        session,
        email="manager@optimal.example",
        full_name="Inactive Manager",
        role=UserRole.MANAGER,
        is_active=False,
    )
    mock_validate.return_value = AzureTokenClaims(
        oid="azure-oid-inactive",
        email="manager@optimal.example",
        name="Inactive Manager",
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


@patch("app.auth.dependencies.settings")
def test_azure_provider_never_uses_dev_auth_fallback(mock_settings, auth_db_client):
    """Production security: AUTH_PROVIDER=azure with DEV_AUTH_ENABLED=false must not auto-login."""
    _patch_azure_settings(mock_settings, dev_auth_enabled=False)
    client, session = auth_db_client
    _seed_user(
        session,
        email="admin@optimal.example",
        full_name="Admin User",
        role=UserRole.ADMIN,
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@patch("app.auth.dependencies.settings")
def test_azure_missing_bearer_returns_401(mock_settings, auth_db_client):
    _patch_azure_settings(mock_settings)
    client, _ = auth_db_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@patch("app.auth.dependencies.settings")
@patch("app.auth.dependencies.validate_azure_access_token")
def test_azure_invalid_token_returns_401(mock_validate, mock_settings, auth_db_client):
    from fastapi import HTTPException

    _patch_azure_settings(mock_settings)
    client, _ = auth_db_client
    mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid token")

    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


@patch("app.auth.dependencies.settings")
def test_dev_auth_still_works_when_provider_is_dev(mock_settings, auth_db_client):
    _patch_dev_settings_for_regression(mock_settings)
    client, _ = auth_db_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["auth_provider"] == "dev"
    assert data["role"] == "admin"


@patch("app.auth.providers.azure.jwt.decode")
@patch("app.auth.providers.azure._rsa_public_key_from_jwk")
@patch("app.auth.providers.azure._fetch_jwks")
@patch("app.auth.providers.azure.jwt.get_unverified_header")
def test_azure_rejects_id_token(mock_header, mock_fetch_jwks, mock_rsa, mock_decode):
    from fastapi import HTTPException

    from app.auth.providers.azure import validate_azure_access_token
    from app.core.config import Settings

    mock_header.return_value = {"kid": "test-kid", "alg": "RS256"}
    mock_fetch_jwks.return_value = {"keys": [{"kid": "test-kid", "kty": "RSA", "n": "x", "e": "y"}]}
    mock_rsa.return_value = "fake-pem"
    mock_decode.return_value = {
        "oid": "oid-123",
        "preferred_username": "user@optimal.example",
        "name": "Test User",
        "aud": "test-api-client-id",
        "nonce": "abc123",
    }

    config = Settings(
        auth_provider="azure",
        azure_tenant_id="test-tenant-id",
        azure_api_client_id="test-api-client-id",
        environment="development",
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_azure_access_token("fake-token", config)

    assert exc_info.value.status_code == 401
    assert "ID tokens are not accepted" in exc_info.value.detail
