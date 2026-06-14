"""Site address extraction and PDF/session display resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.eworks_sync import EworksJob, EworksQuote
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.trade import Trade
from app.schemas.calculation import CalculationBreakdown
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.calculation_session_service import render_combined_works_pdf
from app.services.eworks_pdf_context_service import build_eworks_estimate_pdf_context
from app.services.eworks_site_address_service import (
    extract_site_address_from_raw,
    is_missing_or_placeholder_address,
    resolve_display_property_address,
    resolve_site_address_for_quote,
    resolve_step1_for_display,
)
from app.services.pdf_calculation_context_service import build_pdf_calculation_context
from app.services.quote_assignment_service import _quote_site_address


def _quote(**overrides) -> EworksQuote:
    base = {
        "eworks_quote_id": 12345,
        "quote_ref": "Q12345",
        "customer_name": "ACME Ltd",
        "raw_payload": {},
    }
    base.update(overrides)
    return EworksQuote(**base)


@pytest.fixture()
def address_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (Client, ClientAlias, Trade, EworksQuote, EworksJob, CalculationSession, EworksQuoteAssignment):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    client = Client(name="ACME Ltd", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    db.add_all([client, trade])
    db.flush()
    return db, client, trade


def test_extract_site_address_from_nested_site_address_1():
    raw = {
        "site": {
            "address_1": "10 High Street",
            "city": "London",
            "postcode": "SW1A 1AA",
        }
    }
    assert extract_site_address_from_raw(raw) == "10 High Street, London, SW1A 1AA"


def test_extract_site_address_from_customer_site():
    raw = {
        "customer_site": {
            "address_1": "Unit 4",
            "postcode": "E1 1AA",
        }
    }
    assert extract_site_address_from_raw(raw) == "Unit 4, E1 1AA"


def test_quote_site_address_does_not_return_placeholder(address_db):
    db, _, _ = address_db
    quote = _quote(raw_payload={"site": {"address_1": "22 Baker Street", "city": "London"}})
    db.add(quote)
    db.commit()

    assert _quote_site_address(db, quote) == "22 Baker Street, London"
    assert "Address not specified" not in _quote_site_address(db, quote)


def test_quote_site_address_returns_empty_when_missing(address_db):
    db, _, _ = address_db
    quote = _quote(raw_payload={})
    db.add(quote)
    db.commit()
    assert _quote_site_address(db, quote) == ""


def test_resolve_site_address_falls_back_to_linked_job(address_db):
    db, _, _ = address_db
    quote = _quote(raw_payload={})
    db.add(quote)
    db.flush()
    db.add(
        EworksJob(
            eworks_job_id=999,
            eworks_quote_id=quote.eworks_quote_id,
            address="Job Site, Manchester",
            raw_payload={},
        )
    )
    db.commit()
    assert resolve_site_address_for_quote(db, quote) == "Job Site, Manchester"


def test_session_creation_does_not_persist_placeholder(address_db, monkeypatch):
    db, _, _ = address_db
    quote = _quote(raw_payload={"site": {"address_1": "5 Park Lane", "postcode": "W1"}})
    db.add(quote)
    db.flush()
    assignment = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assignment_type="estimator",
        assignee_kind="registered",
        status="assigned",
    )
    db.add(assignment)
    db.flush()

    monkeypatch.setattr(
        "app.services.quote_assignment_service.try_resolve_rate_rule",
        lambda *_args, **_kwargs: None,
    )
    from app.services.quote_assignment_service import _create_calculation_session_for_assignment

    session = _create_calculation_session_for_assignment(db, assignment=assignment, quote=quote)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    assert step1.property_address == "5 Park Lane, W1"
    assert step1.property_address != "Address not specified"


def test_pdf_context_replaces_placeholder_with_synced_address(address_db):
    db, client, trade = address_db
    quote = _quote(
        raw_payload={
            "site": {
                "address_1": "99 Synced Street",
                "city": "Leeds",
            }
        }
    )
    db.add(quote)
    db.flush()

    session_id = uuid4()
    db.add(
        CalculationSession(
            id=session_id,
            session_token="token-addr",
            source="assignment",
            payload_snapshot={"synced_quote_id": quote.id, "eworks_quote_id": quote.eworks_quote_id},
            step1_snapshot={
                "quote_number": "Q12345",
                "job_number": "12345",
                "client_name": "ACME Ltd",
                "trade_name": "Carpenter",
                "property_address": "Address not specified",
            },
            step2_snapshot=Step2Snapshot(
                works=[WorkBlockSnapshot(scope="Test", engineers_needed=1, engineer_time_value=1)]
            ).model_dump(mode="json"),
            ui_state={
                "last_result": {
                    "breakdown": CalculationBreakdown(
                        labour=[],
                        materials=[],
                        charges=[],
                        subtotal=Decimal("100"),
                        vat_rate=Decimal("20"),
                        vat_total=Decimal("20"),
                        final_total=Decimal("120"),
                        formula_version="test",
                    ).model_dump(mode="json"),
                    "work_breakdowns": [
                        {
                            "work_index": 0,
                            "scope": "Test",
                            "breakdown": {
                                "labour": [],
                                "materials": [],
                                "charges": [],
                                "subtotal": "100",
                                "vat_rate": "20",
                                "vat_total": "20",
                                "final_total": "120",
                                "formula_version": "test",
                            },
                        }
                    ],
                }
            },
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
            locked=True,
        )
    )
    db.commit()

    ctx = build_pdf_calculation_context(db, db.get(CalculationSession, session_id), allow_recalculate=False)
    assert ctx.step1.property_address == "99 Synced Street, Leeds"


def test_pdf_shows_dash_when_no_address_exists():
    step1 = Step1Snapshot(
        quote_number="Q000",
        job_number="1",
        client_name="ACME Ltd",
        trade_name="Carpenter",
        property_address="Address not specified",
    )
    step2 = Step2Snapshot(works=[WorkBlockSnapshot(scope="Test")])
    breakdown = CalculationBreakdown(
        labour=[],
        materials=[],
        charges=[],
        subtotal=Decimal("0"),
        vat_rate=Decimal("20"),
        vat_total=Decimal("0"),
        final_total=Decimal("0"),
        formula_version="test",
    )
    context = build_eworks_estimate_pdf_context(
        step1=step1,
        step2=step2,
        breakdown=breakdown,
        client_view={"calculation": breakdown.model_dump(mode="json")},
        show_internal_notes=False,
    )
    assert context["property_address"] == "—"
    assert "Address not specified" not in context["property_address"]


def test_existing_session_displays_refreshed_address(address_db):
    db, client, trade = address_db
    quote = _quote(raw_payload={"site": {"address_1": "Refreshed Road", "postcode": "M1 1AE"}})
    db.add(quote)
    db.flush()
    session_id = uuid4()
    session = CalculationSession(
        id=session_id,
        session_token="token-refresh",
        source="assignment",
        payload_snapshot={"synced_quote_id": quote.id},
        step1_snapshot={
            "quote_number": "Q12345",
            "job_number": "12345",
            "client_name": "ACME Ltd",
            "trade_name": "Carpenter",
            "property_address": "Address not specified",
        },
        step2_snapshot=Step2Snapshot(
            works=[WorkBlockSnapshot(scope="Scope", engineers_needed=1, engineer_time_value=1)]
        ).model_dump(mode="json"),
        ui_state={
            "last_result": {
                "breakdown": CalculationBreakdown(
                    labour=[],
                    materials=[],
                    charges=[],
                    subtotal=Decimal("50"),
                    vat_rate=Decimal("20"),
                    vat_total=Decimal("10"),
                    final_total=Decimal("60"),
                    formula_version="test",
                ).model_dump(mode="json"),
                "work_breakdowns": [],
            }
        },
        client_id=client.id,
        trade_id=trade.id,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        status="submitted",
        submitted_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        locked=True,
    )
    db.add(session)
    db.commit()

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    resolved = resolve_step1_for_display(db, session, step1)
    assert resolved.property_address == "Refreshed Road, M1 1AE"
    assert is_missing_or_placeholder_address(resolved.property_address) is False


def test_client_and_optimal_pdf_use_same_corrected_site_address(address_db):
    db, client, trade = address_db
    quote = _quote(raw_payload={"site": {"address_1": "Shared Street", "city": "Bristol"}})
    db.add(quote)
    db.flush()
    session_id = uuid4()
    db.add(
        CalculationSession(
            id=session_id,
            session_token="token-shared",
            source="assignment",
            payload_snapshot={"synced_quote_id": quote.id},
            step1_snapshot={
                "quote_number": "Q12345",
                "job_number": "12345",
                "client_name": "ACME Ltd",
                "trade_name": "Carpenter",
                "property_address": "Address not specified",
            },
            step2_snapshot=Step2Snapshot(
                works=[WorkBlockSnapshot(scope="Scope", engineers_needed=1, engineer_time_value=1)]
            ).model_dump(mode="json"),
            ui_state={
                "last_result": {
                    "breakdown": CalculationBreakdown(
                        labour=[],
                        materials=[],
                        charges=[],
                        subtotal=Decimal("50"),
                        vat_rate=Decimal("20"),
                        vat_total=Decimal("10"),
                        final_total=Decimal("60"),
                        formula_version="test",
                    ).model_dump(mode="json"),
                    "work_breakdowns": [
                        {
                            "work_index": 0,
                            "scope": "Scope",
                            "breakdown": {
                                "labour": [{"label": "Labour", "formula": "x", "total": "50"}],
                                "materials": [],
                                "charges": [],
                                "subtotal": "50",
                                "vat_rate": "20",
                                "vat_total": "10",
                                "final_total": "60",
                                "formula_version": "test",
                            },
                        }
                    ],
                }
            },
            client_id=client.id,
            trade_id=trade.id,
            expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            status="submitted",
            submitted_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
            locked=True,
        )
    )
    db.commit()

    client_pdf, _, _ = render_combined_works_pdf(
        db, session_id=session_id, work_indexes=[0], view_type="client"
    )
    optimal_pdf, _, _ = render_combined_works_pdf(
        db, session_id=session_id, work_indexes=[0], view_type="optimal"
    )
    assert b"Shared Street" in client_pdf
    assert b"Shared Street" in optimal_pdf
    assert b"Address not specified" not in client_pdf
    assert b"Address not specified" not in optimal_pdf


def test_resolve_display_property_address_never_returns_placeholder(address_db):
    db, client, trade = address_db
    quote = _quote(raw_payload={})
    db.add(quote)
    db.flush()
    session = CalculationSession(
        id=uuid4(),
        session_token="token-empty",
        source="test",
        payload_snapshot={"synced_quote_id": quote.id},
        step1_snapshot={
            "quote_number": "Q1",
            "job_number": "1",
            "client_name": "ACME Ltd",
            "trade_name": "Carpenter",
            "property_address": "Address not specified",
        },
        step2_snapshot={},
        client_id=client.id,
        trade_id=trade.id,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db.add(session)
    db.commit()
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    assert resolve_display_property_address(db, session, step1) == ""
