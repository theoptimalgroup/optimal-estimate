"""Unit tests for manager quote PDF downloads."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User


def _patch_dev_user(mock_settings, *, role: str):
    mock_settings.auth_provider = "dev"
    mock_settings.dev_auth_enabled = True
    mock_settings.dev_user_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    mock_settings.dev_user_email = "staff@optimal.example"
    mock_settings.dev_user_name = "Staff User"
    mock_settings.dev_user_role = role
    mock_settings.dev_user_is_active = True
    mock_settings.dev_auth_auto_create_user = False


def _step1(*, quote_number: str) -> dict:
    return {
        "quote_number": quote_number,
        "job_number": "JOB-001",
        "client_name": "ACME Ltd",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
    }


def _ui_state(final_total: str) -> dict:
    breakdown = {
        "labour": [{"label": "Labour", "formula": "fixed", "total": "100.00"}],
        "materials": [{"label": "Materials", "formula": "fixed", "total": "20.00"}],
        "charges": [],
        "subtotal": "120.00",
        "vat_rate": "20",
        "vat_total": "24.00",
        "final_total": final_total,
        "formula_version": "1.0.0",
    }
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": breakdown,
            "work_breakdowns": [
                {
                    "work_index": 0,
                    "scope": "Submitted work",
                    "breakdown": breakdown,
                }
            ],
        },
    }


@pytest.fixture()
def pdf_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    session.add_all([client, trade])
    session.flush()

    submitted_id = uuid4()
    draft_id = uuid4()
    session.add_all(
        [
            CalculationSession(
                id=submitted_id,
                session_token="token-submitted",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1(quote_number="Q22100"),
                step2_snapshot={"works": [{"scope": "Submitted work", "product_code": "P-001"}]},
                ui_state=_ui_state("124.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="submitted",
                submitted_at=datetime(2026, 6, 5, 15, 48, tzinfo=timezone.utc),
            ),
            CalculationSession(
                id=draft_id,
                session_token="token-draft",
                source="test",
                payload_snapshot={},
                step1_snapshot=_step1(quote_number="Q22101"),
                step2_snapshot={"works": [{"scope": "Draft work"}]},
                ui_state=_ui_state("100.00"),
                client_id=client.id,
                trade_id=trade.id,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                status="in_progress",
            ),
        ]
    )
    session.commit()
    return session, submitted_id, draft_id


@pytest.fixture()
def pdf_api_client(pdf_db_session):
    db, _, _ = pdf_db_session

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["manager", "admin"])
@patch("app.api.v1.manager.render_manager_quote_pdf")
@patch("app.auth.dependencies.settings")
def test_manager_roles_can_download_pdfs(mock_settings, mock_render_pdf, pdf_api_client, pdf_db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, submitted_id, _ = pdf_db_session
    mock_render_pdf.return_value = (b"%PDF-1.4 test content", "Q22100_Client_view.pdf", "application/pdf")

    for view in ("client", "internal", "combined", "all-trades"):
        response = pdf_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/{view}")
        assert response.status_code == 200, view
        assert len(response.content) > 0


@pytest.mark.parametrize("role", ["engineer", "estimator", "client"])
@patch("app.auth.dependencies.settings")
def test_non_manager_roles_blocked_from_pdf(mock_settings, pdf_api_client, pdf_db_session, role):
    _patch_dev_user(mock_settings, role=role)
    _, submitted_id, _ = pdf_db_session

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/client")
    assert response.status_code == 403


@patch("app.auth.dependencies.settings")
def test_pdf_rejects_non_submitted_session(mock_settings, pdf_api_client, pdf_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, _, draft_id = pdf_db_session

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{draft_id}/pdf/client")
    assert response.status_code == 409


@patch("app.auth.dependencies.settings")
def test_pdf_rejects_unknown_session(mock_settings, pdf_api_client, pdf_db_session):
    _patch_dev_user(mock_settings, role="manager")

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{uuid4()}/pdf/client")
    assert response.status_code == 404


@patch("app.services.manager_quote_pdf_service.render_combined_works_pdf")
@patch("app.auth.dependencies.settings")
def test_client_pdf_excludes_internal_fields(
    mock_settings,
    mock_render_combined,
    pdf_api_client,
    pdf_db_session,
):
    _patch_dev_user(mock_settings, role="manager")
    _, submitted_id, _ = pdf_db_session

    mock_render_combined.return_value = (b"<html>QUOTE SUMMARY</html>", "Q22100_Client_view.html", "text/html; charset=utf-8")

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/client")
    assert response.status_code == 200
    mock_render_combined.assert_called_once()
    _, kwargs = mock_render_combined.call_args
    assert kwargs["view_type"] == "client"
    assert kwargs["work_indexes"] == [0]

    body = response.content.decode("utf-8")
    assert "profit" not in body.lower()
    assert "margin" not in body.lower()


@patch("app.services.manager_quote_pdf_service.render_combined_works_pdf")
@patch("app.auth.dependencies.settings")
def test_internal_pdf_uses_optimal_view(
    mock_settings,
    mock_render_combined,
    pdf_api_client,
    pdf_db_session,
):
    _patch_dev_user(mock_settings, role="manager")
    _, submitted_id, _ = pdf_db_session

    mock_render_combined.return_value = (
        b"<html>OPTIMAL QUOTE SUMMARY</html>",
        "Q22100_optimal_view.html",
        "text/html; charset=utf-8",
    )

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/internal")
    assert response.status_code == 200
    mock_render_combined.assert_called_once()
    _, kwargs = mock_render_combined.call_args
    assert kwargs["view_type"] == "optimal"


@patch("app.services.calculation_session_pdf_service.calculate_session")
@patch("app.auth.dependencies.settings")
def test_combined_pdf_uses_cached_result_for_submitted_session(
    mock_settings,
    mock_calculate,
    pdf_api_client,
    pdf_db_session,
):
    _patch_dev_user(mock_settings, role="manager")
    _, submitted_id, _ = pdf_db_session

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/combined")
    assert response.status_code == 200
    assert len(response.content) > 0
    mock_calculate.assert_not_called()


@patch("app.auth.dependencies.settings")
def test_combined_pdf_content_type_is_pdf_or_html(mock_settings, pdf_api_client, pdf_db_session):
    _patch_dev_user(mock_settings, role="manager")
    _, submitted_id, _ = pdf_db_session

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/combined")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(("application/pdf", "text/html"))


def _five_work_step2() -> dict:
    skills = ["Carpenter", "Painter", "Plumber", "Electrician", "Decorator"]
    return {
        "works": [
            {
                "scope": f"{skill} scope {index + 1}",
                "product_code": f"P-{index + 1:03d}",
                "skill_required": skill,
            }
            for index, skill in enumerate(skills)
        ],
        "congestion_required": True,
        "congestion_amount": "10.00",
        "travel_charge": "5.00",
        "other_charge": "0",
    }


def _five_work_ui_state() -> dict:
    work_breakdowns = []
    for index in range(5):
        labour = Decimal("100") + Decimal(index * 10)
        materials = Decimal("20") + Decimal(index * 5)
        work_breakdowns.append(
            {
                "work_index": index,
                "breakdown": {
                    "labour": [{"label": "Labour", "total": str(labour)}],
                    "materials": [{"label": "Materials", "total": str(materials)}],
                    "charges": [],
                },
            }
        )
    works_subtotal = Decimal("650")
    additional_charges = Decimal("15")
    subtotal = works_subtotal + additional_charges
    vat_total = subtotal * Decimal("0.20")
    final_total = subtotal + vat_total
    return {
        "current_step": 3,
        "max_reachable_step": 3,
        "last_result": {
            "breakdown": {
                "final_total": str(final_total.quantize(Decimal("0.01"))),
                "labour": [{"total": "550.00"}],
                "materials": [{"total": "100.00"}],
                "charges": [
                    {"label": "Congestion", "total": "10.00"},
                    {"label": "Travel", "total": "5.00"},
                ],
                "vat_total": str(vat_total.quantize(Decimal("0.01"))),
                "vat_rate": "20",
            },
            "work_breakdowns": work_breakdowns,
        },
    }


@pytest.fixture()
def all_trades_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, AuditLog):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    for trade_name in ("Carpenter", "Painter", "Plumber", "Electrician", "Decorator"):
        session.add(Trade(name=trade_name, is_active=True))
    session.add(client)
    session.flush()

    submitted_id = uuid4()
    session.add(
        CalculationSession(
            id=submitted_id,
            session_token="token-all-trades",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1(quote_number="Q22100"),
            step2_snapshot=_five_work_step2(),
            ui_state=_five_work_ui_state(),
            client_id=client.id,
            trade_id=session.query(Trade).filter_by(name="Carpenter").one().id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 5, 15, 48, tzinfo=timezone.utc),
        )
    )
    session.commit()
    return session, submitted_id


@pytest.fixture()
def all_trades_api_client(all_trades_db_session):
    db, _ = all_trades_db_session

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@patch("app.auth.dependencies.settings")
def test_all_trades_pdf_endpoint_returns_flat_work_list(
    mock_settings,
    all_trades_api_client,
    all_trades_db_session,
):
    _patch_dev_user(mock_settings, role="manager")
    _, submitted_id = all_trades_db_session

    response = all_trades_api_client.get(f"/api/v1/manager/quotes/{submitted_id}/pdf/all-trades")
    assert response.status_code == 200
    assert len(response.content) > 0

    body = response.content.decode("utf-8")
    assert "All Trades / Skills" in body
    assert body.index("Carpenter scope 1") < body.index("Painter scope 2")
    assert body.index("Painter scope 2") < body.index("Plumber scope 3")
    assert body.index("Plumber scope 3") < body.index("Electrician scope 4")
    assert body.index("Electrician scope 4") < body.index("Decorator scope 5")
    assert body.count("Works subtotal") == 1
    assert body.count("Congestion") == 1
    assert body.count("Travel") == 1
    assert "Final total" in body

    visible_body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    lowered = visible_body.lower()
    forbidden = ("profit", "margin", "formula", "denominator", "session_token", "token-all-trades")
    for term in forbidden:
        assert term not in lowered, term


@patch("app.auth.dependencies.settings")
def test_all_trades_pdf_rejects_non_submitted_session(
    mock_settings,
    pdf_api_client,
    pdf_db_session,
):
    _patch_dev_user(mock_settings, role="manager")
    _, _, draft_id = pdf_db_session

    response = pdf_api_client.get(f"/api/v1/manager/quotes/{draft_id}/pdf/all-trades")
    assert response.status_code == 409
