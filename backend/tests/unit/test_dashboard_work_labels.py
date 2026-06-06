"""Tests for dashboard work item display labels."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.product import Product
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.calculation_session_service import _build_dashboard_work_item, list_submitted_quotes


def _step1() -> dict:
    return {
        "quote_number": "Q22091",
        "job_number": "29191",
        "client_name": "Unknown Customer",
        "trade_name": "Carpenter",
        "property_address": "1 Test Street",
        "congestion_required": False,
        "congestion_amount": "0",
        "travel": "0",
    }


def test_build_dashboard_work_item_uses_product_name():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, AuditLog, Product):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(
        Product(
            id=1,
            eworks_item_id=1403,
            product_name="Carpenter",
            product_code="CARP-001",
            cost_price=Decimal("0"),
            selling_price=Decimal("100"),
            margin=Decimal("0"),
        )
    )
    db.commit()

    block = WorkBlockSnapshot(
        scope="- Drill and inject damp-proof course.",
        selected_product_id=1,
        product_name="Carpenter",
        product_code="CARP-001",
    )
    item = _build_dashboard_work_item(
        db,
        index=0,
        block=block,
        labour_subtotal=Decimal("1.00"),
        materials_subtotal=Decimal("0.20"),
        work_internal_notes=None,
    )

    assert item.display_label == "Carpenter · CARP-001"
    assert item.product_name == "Carpenter"


def test_build_dashboard_work_item_resolves_product_from_catalog():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, AuditLog, Product):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(
        Product(
            id=5,
            eworks_item_id=999,
            product_name="Damp Proof Course",
            product_code="DPC-01",
            cost_price=Decimal("0"),
            selling_price=Decimal("50"),
            margin=Decimal("0"),
        )
    )
    db.commit()

    block = WorkBlockSnapshot(
        scope="- Drill and inject damp-proof course.",
        selected_product_id=5,
    )
    item = _build_dashboard_work_item(
        db,
        index=0,
        block=block,
        labour_subtotal=None,
        materials_subtotal=None,
        work_internal_notes=None,
    )

    assert item.display_label == "Damp Proof Course · DPC-01"


def test_list_submitted_quotes_includes_display_label_not_work_number():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (User, Client, ClientAlias, Trade, CalculationSession, AuditLog, Product):
        model.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    client = Client(name="Unknown Customer", default_vat_rate=Decimal("20"))
    trade = Trade(name="Carpenter", is_active=True)
    db.add_all([client, trade])
    db.flush()

    db.add(
        CalculationSession(
            id=uuid4(),
            session_token="token-review",
            source="test",
            payload_snapshot={},
            step1_snapshot=_step1(),
            step2_snapshot=Step2Snapshot(
                works=[
                    WorkBlockSnapshot(
                        scope="- Drill and inject damp-proof course.",
                        product_name="Carpenter",
                        product_code="CARP-001",
                    )
                ]
            ).model_dump(mode="json"),
            ui_state={
                "last_result": {
                    "breakdown": {"final_total": "1.44"},
                    "work_breakdowns": [
                        {
                            "work_index": 0,
                            "breakdown": {
                                "labour": [{"label": "Labour", "formula": "x", "total": "1.00"}],
                                "materials": [{"label": "Materials", "formula": "x", "total": "0.20"}],
                                "charges": [],
                                "subtotal": "1.20",
                                "vat_rate": "20",
                                "vat_total": "0.24",
                                "final_total": "1.44",
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
            submitted_at=datetime(2026, 6, 5, 17, 46, tzinfo=timezone.utc),
        )
    )
    db.commit()

    quotes = list_submitted_quotes(db).quotes
    assert len(quotes) == 1
    work = quotes[0].works[0]
    assert work.display_label == "Carpenter · CARP-001"
    assert work.display_label != "Work 1"
