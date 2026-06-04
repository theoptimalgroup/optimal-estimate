"""Unit tests for dev auth foundation."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import require_dashboard_access, require_roles
from app.auth.resolution import resolve_dev_authenticated_user
from app.core.config import Settings
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
from app.models.user import User


ENV_ONLY_EMAIL = "dev-only@optimal.example"


def _patch_dev_settings(mock_settings, **overrides):
    defaults = {
        "auth_provider": "dev",
        "is_azure_auth": False,
        "is_dev_auth": True,
        "dev_auth_enabled": True,
        "dev_user_id": "dev-user-1",
        "dev_user_email": ENV_ONLY_EMAIL,
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


def _seed_user(
    session,
    *,
    email: str,
    full_name: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
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


@patch("app.auth.dependencies.settings")
def test_auth_me_falls_back_to_env_when_user_missing(mock_settings, auth_db_client):
    _patch_dev_settings(mock_settings)
    client, _ = auth_db_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {
        "id": "dev-user-1",
        "email": ENV_ONLY_EMAIL,
        "name": "Env User",
        "role": "admin",
        "is_active": True,
        "auth_provider": "dev",
    }


@patch("app.auth.dependencies.settings")
def test_auth_me_returns_db_role_and_name_when_email_matches(mock_settings, auth_db_client):
    _patch_dev_settings(
        mock_settings,
        dev_user_email="manager@optimal.example",
        dev_user_name="Env Manager Name",
        dev_user_role="admin",
    )
    client, session = auth_db_client
    db_user = _seed_user(
        session,
        email="manager@optimal.example",
        full_name="Manager From DB",
        role=UserRole.MANAGER,
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(db_user.id)
    assert data["email"] == "manager@optimal.example"
    assert data["name"] == "Manager From DB"
    assert data["role"] == "manager"
    assert data["is_active"] is True
    assert data["auth_provider"] == "dev"


@patch("app.auth.dependencies.settings")
def test_auth_me_returns_403_when_db_user_inactive(mock_settings, auth_db_client):
    _patch_dev_settings(mock_settings, dev_user_email="manager@optimal.example")
    client, session = auth_db_client
    _seed_user(
        session,
        email="manager@optimal.example",
        full_name="Inactive Manager",
        role=UserRole.MANAGER,
        is_active=False,
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


@patch("app.auth.dependencies.settings")
def test_auth_me_returns_401_when_dev_auth_disabled(mock_settings, auth_db_client):
    _patch_dev_settings(mock_settings, dev_auth_enabled=False)
    client, _ = auth_db_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@patch("app.auth.dependencies.settings")
def test_auth_me_returns_403_when_env_user_inactive(mock_settings, auth_db_client):
    _patch_dev_settings(mock_settings, dev_user_is_active=False)
    client, _ = auth_db_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


def test_invalid_dev_user_role_is_handled_safely(auth_db):
    config = Settings(
        dev_auth_enabled=True,
        dev_user_id="dev-user-1",
        dev_user_email=ENV_ONLY_EMAIL,
        dev_user_name="Env User",
        dev_user_role="superadmin",
        dev_user_is_active=True,
        dev_auth_auto_create_user=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        resolve_dev_authenticated_user(auth_db, config)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid authentication configuration"


@patch("app.auth.dependencies.settings")
def test_get_current_user_supports_client_role(mock_settings, auth_db_client):
    _patch_dev_settings(
        mock_settings,
        dev_user_id="dev-client-1",
        dev_user_email="client@optimal.example",
        dev_user_name="Client User",
        dev_user_role="client",
    )
    client, _ = auth_db_client

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["data"]["role"] == "client"


def test_auth_me_email_lookup_is_case_insensitive(auth_db):
    config = Settings(
        dev_auth_enabled=True,
        dev_user_email="Manager@Optimal.Example",
        dev_user_name="Env Name",
        dev_user_role="admin",
        dev_user_is_active=True,
        dev_auth_auto_create_user=False,
    )
    db_user = _seed_user(
        auth_db,
        email="manager@optimal.example",
        full_name="Manager From DB",
        role=UserRole.MANAGER,
    )

    user = resolve_dev_authenticated_user(auth_db, config)

    assert user.id == str(db_user.id)
    assert user.role == UserRole.MANAGER


def test_dev_auth_auto_create_user(auth_db):
    config = Settings(
        dev_auth_enabled=True,
        dev_user_email="new-user@optimal.example",
        dev_user_name="New User",
        dev_user_role="estimator",
        dev_user_is_active=True,
        dev_auth_auto_create_user=True,
    )

    user = resolve_dev_authenticated_user(auth_db, config)

    assert user.email == "new-user@optimal.example"
    assert user.name == "New User"
    assert user.role == UserRole.ESTIMATOR
    assert auth_db.scalar(select(User).where(User.email == "new-user@optimal.example")) is not None


def _build_role_test_app(db_session, *allowed_roles: UserRole) -> FastAPI:
    test_app = FastAPI()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db

    @test_app.get("/protected")
    def protected(user=Depends(require_roles(*allowed_roles))):
        return {"role": user.role.value}

    return test_app


@patch("app.auth.dependencies.settings")
def test_require_roles_allows_db_role(mock_settings, auth_db):
    _patch_dev_settings(
        mock_settings,
        dev_user_email="admin@optimal.example",
        dev_user_role="engineer",
    )
    _seed_user(auth_db, email="admin@optimal.example", full_name="Admin User", role=UserRole.ADMIN)

    with TestClient(_build_role_test_app(auth_db, UserRole.ADMIN)) as client:
        response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"role": "admin"}


@patch("app.auth.dependencies.settings")
def test_require_roles_blocks_db_role(mock_settings, auth_db):
    _patch_dev_settings(
        mock_settings,
        dev_user_email="engineer@optimal.example",
        dev_user_role="admin",
    )
    _seed_user(auth_db, email="engineer@optimal.example", full_name="Engineer User", role=UserRole.ENGINEER)

    with TestClient(_build_role_test_app(auth_db, UserRole.ADMIN, UserRole.MANAGER)) as client:
        response = client.get("/protected")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def _build_dashboard_access_test_app(db_session) -> FastAPI:
    test_app = FastAPI()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db

    @test_app.get("/check")
    def check(_access=Depends(require_dashboard_access)):
        return {
            "method": _access.method,
            "role": _access.user.role.value if _access.user else None,
        }

    return test_app


@patch("app.auth.dependencies.settings")
def test_dashboard_uses_db_manager_role(mock_settings, auth_db):
    _patch_dev_settings(
        mock_settings,
        dev_user_email="manager@optimal.example",
        dev_user_role="engineer",
    )
    _seed_user(auth_db, email="manager@optimal.example", full_name="Manager User", role=UserRole.MANAGER)

    with TestClient(_build_dashboard_access_test_app(auth_db)) as client:
        response = client.get("/check")

    assert response.status_code == 200
    assert response.json() == {"method": "user", "role": "manager"}


@patch("app.auth.dependencies.settings")
def test_dashboard_blocks_db_engineer_role(mock_settings, auth_db):
    _patch_dev_settings(
        mock_settings,
        dev_user_email="manager@optimal.example",
        dev_user_role="manager",
    )
    _seed_user(auth_db, email="manager@optimal.example", full_name="Manager User", role=UserRole.ENGINEER)

    with TestClient(_build_dashboard_access_test_app(auth_db)) as client:
        response = client.get("/check")

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"
