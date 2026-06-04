"""Unit tests for engineer-safe session API and service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.engineer_session import router as engineer_router
from app.db.session import get_db
from app.models.user import User
from app.schemas.engineer_session import EngineerSessionRead, EngineerSiteVisitUpdate
from app.services.engineer_session_service import assert_no_financial_keys


@pytest.fixture()
def sample_session_read() -> EngineerSessionRead:
    return EngineerSessionRead(
        session_id=uuid4(),
        status="in_progress",
        expires_at=datetime.now(timezone.utc),
        job={
            "quote_number": "Q-1",
            "job_number": "J-1",
            "client_name": "Acme",
            "trade_name": "Electrical",
            "property_address": "1 High Street",
            "engineer_name": "Sam",
            "status": "in_progress",
        },
        site_visit={
            "scope": "Test scope",
            "site_notes": "Notes",
            "engineer_count": 1,
            "labourer_count": 0,
            "duration_type": "hourly",
            "hours": Decimal("2"),
            "attachments": [],
            "parking_required": False,
            "congestion_required": False,
            "ulez_required": False,
            "waste_required": False,
        },
    )


def test_assert_no_financial_keys_passes_engineer_payload(sample_session_read):
    payload = sample_session_read.model_dump(mode="json")
    assert_no_financial_keys(payload)
    assert "resolved" not in json.dumps(payload)


def test_assert_no_financial_keys_raises_on_breakdown():
    with pytest.raises(AssertionError, match="breakdown"):
        assert_no_financial_keys({"job": {"quote_number": "Q"}, "breakdown": {"final_total": 10}})


def _build_engineer_test_app(db_session):
    test_app = FastAPI()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.include_router(engineer_router, prefix="/api/v1")
    return test_app


@pytest.fixture()
def engineer_auth_db():
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


@patch("app.auth.dependencies.settings")
@patch("app.services.engineer_session_service.get_engineer_session")
def test_engineer_route_allowed_for_engineer(mock_get_session, mock_settings, sample_session_read, engineer_auth_db):
    mock_get_session.return_value = sample_session_read
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_role = "engineer"
    mock_settings.dev_user_id = "u1"
    mock_settings.dev_user_email = "e@example.com"
    mock_settings.dev_user_name = "Engineer"
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False

    test_app = _build_engineer_test_app(engineer_auth_db)
    session_id = sample_session_read.session_id

    with patch("app.api.v1.engineer_session.get_engineer_session", return_value=sample_session_read):
        with TestClient(test_app) as client:
            response = client.get(
                f"/api/v1/engineer/sessions/{session_id}",
                headers={"X-Session-Token": "token"},
            )

    assert response.status_code == 200
    data = response.json()["data"]
    assert_no_financial_keys(data)


@patch("app.auth.dependencies.settings")
def test_engineer_route_blocks_manager(mock_settings, engineer_auth_db):
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_role = "manager"
    mock_settings.dev_user_id = "u1"
    mock_settings.dev_user_email = "m@example.com"
    mock_settings.dev_user_name = "Manager"
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False

    test_app = _build_engineer_test_app(engineer_auth_db)

    with TestClient(test_app) as client:
        response = client.get(
            f"/api/v1/engineer/sessions/{uuid4()}",
            headers={"X-Session-Token": "token"},
        )

    assert response.status_code == 403


def test_engineer_site_visit_update_validates_hourly_hours():
    payload = EngineerSiteVisitUpdate(
        engineer_count=1,
        labourer_count=0,
        duration_type="hourly",
        hours=None,
    )
    with pytest.raises(ValueError, match="Hours"):
        payload.model_validate_duration()
