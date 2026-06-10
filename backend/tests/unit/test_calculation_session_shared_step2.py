"""Unit tests for shared quote-level Step 2 work block snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.exceptions import AppError
from app.core.security import UserRole, get_password_hash
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.quote_work_attachment import QuoteWorkAttachment
from app.models.quote_work_snapshot import QuoteWorkSnapshot
from app.models.rate_rule import RateRule
from app.models.support import AuditLog
from app.models.trade import Trade
from app.models.user import User
from app.schemas.eworks_link import Step2Snapshot, UpdateCalculationSessionRequest, WorkBlockSnapshot
from app.services.calculation_session_service import (
    add_session_attachment,
    build_calculation_session_read,
    submit_session,
    update_session_step2,
)
from app.services.quote_assignment_service import start_assignment_estimate
from app.services.quote_work_snapshot_service import (
    get_quote_work_snapshot,
    save_shared_step2,
    user_can_access_quote_work_snapshot,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [
        User.__table__,
        AuditLog.__table__,
        Client.__table__,
        ClientAlias.__table__,
        Trade.__table__,
        RateRule.__table__,
        CalculationSession.__table__,
        CalculationSessionVersion.__table__,
        EworksQuote.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
        EworksQuoteAppointment.__table__,
        EworksQuoteAssignment.__table__,
        QuoteWorkAttachment.__table__,
        QuoteWorkSnapshot.__table__,
    ]:
        table.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    now = datetime.now(timezone.utc)
    vitor_id = uuid4()
    other_id = uuid4()
    outsider_id = uuid4()
    third_id = uuid4()
    manager_id = uuid4()
    vitor = User(
        id=vitor_id,
        email="vitor.santo@theoptimalgroup.co.uk",
        full_name="Vitor Espirito Santo",
        password_hash=get_password_hash("eng12345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    other = User(
        id=other_id,
        email="other.engineer@theoptimalgroup.co.uk",
        full_name="Other Engineer",
        password_hash=get_password_hash("eng22345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    outsider = User(
        id=outsider_id,
        email="outsider.engineer@theoptimalgroup.co.uk",
        full_name="Outsider Engineer",
        password_hash=get_password_hash("eng32345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    third = User(
        id=third_id,
        email="third.engineer@theoptimalgroup.co.uk",
        full_name="Third Engineer",
        password_hash=get_password_hash("eng42345"),
        role=UserRole.ENGINEER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    manager = User(
        id=manager_id,
        email="manager@theoptimalgroup.co.uk",
        full_name="Manager User",
        password_hash=get_password_hash("mgr12345"),
        role=UserRole.MANAGER.value,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    trade = Trade(id=uuid4(), name="Carpenter", is_active=True, created_at=now, updated_at=now)
    rule = RateRule(
        client_id=None,
        trade_id=trade.id,
        formula_source="xlsx",
        version="trade-default-carpenter",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0.15"),
        hourly_overhead_pct=Decimal("0.30"),
        daily_overhead_pct=Decimal("0.20"),
        daily_overhead_long_job_pct=Decimal("0.15"),
        labourer_hourly_cost=Decimal("18.75"),
        labourer_daily_cost=Decimal("150"),
        material_charge_denominator=Decimal("0.20"),
        parking_charge_denominator=Decimal("0.20"),
        congestion_charge_denominator=Decimal("0.20"),
        mround_increment=Decimal("5"),
        oj_uplift_pct=Decimal("10"),
        nhs_overhead_uplift_pct=Decimal("15"),
        eaf_flat_fee=Decimal("1"),
        xlsx_client_name="Trade default",
        xlsx_trade_name="Carpenter",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=datetime(2024, 1, 1).date(),
        is_active=True,
    )
    session.add_all([vitor, other, outsider, third, manager, trade, rule])
    session.commit()
    yield session
    session.close()


def _engineer_user(db_session, *, email: str) -> AuthenticatedUser:
    user = db_session.query(User).filter(User.email == email).one()
    return AuthenticatedUser(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        role=UserRole.ENGINEER,
        is_active=True,
        auth_provider="dev",
    )


def _seed_quote_with_assignments(db_session, *, eworks_quote_id: int = 22179, quote_ref: str = "Q22179"):
    quote = EworksQuote(
        eworks_quote_id=eworks_quote_id,
        quote_ref=quote_ref,
        customer_name="Test Customer",
        status="1",
        tags="Booked (Quotes)",
        raw_payload={"site_address": "1 Test Street"},
    )
    db_session.add(quote)
    db_session.flush()

    vitor = db_session.query(User).filter(User.email == "vitor.santo@theoptimalgroup.co.uk").one()
    other = db_session.query(User).filter(User.email == "other.engineer@theoptimalgroup.co.uk").one()

    assignment_a = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assignment_type="engineer",
        assignee_kind="registered",
        assigned_user_id=vitor.id,
        assigned_user_email=vitor.email,
        assigned_user_name=vitor.full_name,
        status="assigned",
    )
    assignment_b = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assignment_type="engineer",
        assignee_kind="registered",
        assigned_user_id=other.id,
        assigned_user_email=other.email,
        assigned_user_name=other.full_name,
        status="assigned",
    )
    db_session.add_all([assignment_a, assignment_b])
    db_session.commit()
    return quote, assignment_a, assignment_b


def _dishwasher_block(**overrides) -> WorkBlockSnapshot:
    block = WorkBlockSnapshot(
        scope="Repair dishwasher",
        selected_product_id=42,
        product_name="Dishwasher",
        product_code="DW-001",
        is_custom_scope=False,
    )
    return block.model_copy(update=overrides)


def _custom_block(**overrides) -> WorkBlockSnapshot:
    block = WorkBlockSnapshot(
        scope="Custom repair scope",
        is_custom_scope=True,
        custom_title="Bespoke kitchen work",
    )
    return block.model_copy(update=overrides)


def _make_upload(content: bytes = b"fake-image-bytes", filename: str = "photo.jpg") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": "image/jpeg"})


def _start_sessions(db_session):
    quote, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")
    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    assert calc_a is not None and calc_b is not None
    return quote, assignment_a, assignment_b, vitor, other, calc_a, calc_b


def _patch_step2(db_session, calc_session, step2: Step2Snapshot):
    return update_session_step2(
        db_session,
        session_id=calc_session.id,
        session_token=calc_session.session_token,
        payload=UpdateCalculationSessionRequest(step2=step2),
    )


def test_engineer_a_product_scope_visible_to_engineer_b(db_session):
    _, _, _, _, _, calc_a, calc_b = _start_sessions(db_session)
    step2 = Step2Snapshot(works=[_dishwasher_block(scope="Supply and fit dishwasher Q22179")])
    _patch_step2(db_session, calc_a, step2)
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert read_b.step2.works[0].product_name == "Dishwasher"
    assert read_b.step2.works[0].scope == "Supply and fit dishwasher Q22179"
    assert read_b.shared_step2 is not None
    assert read_b.shared_step2.updated_by_name == "Vitor Espirito Santo"


def test_engineer_c_assigned_later_sees_same_work_blocks(db_session):
    quote, _, _, vitor, _, calc_a, _ = _start_sessions(db_session)
    step2 = Step2Snapshot(works=[_dishwasher_block(scope="Shared initial scope")])
    _patch_step2(db_session, calc_a, step2)
    db_session.commit()

    third = _engineer_user(db_session, email="third.engineer@theoptimalgroup.co.uk")
    assignment_c = EworksQuoteAssignment(
        synced_quote_id=quote.id,
        eworks_quote_id=quote.eworks_quote_id,
        quote_ref=quote.quote_ref,
        assignment_type="engineer",
        assignee_kind="registered",
        assigned_user_id=UUID(third.id),
        assigned_user_email=third.email,
        assigned_user_name=third.name,
        status="assigned",
    )
    db_session.add(assignment_c)
    db_session.commit()

    session_c = start_assignment_estimate(db_session, assignment_c.id, third)
    calc_c = db_session.get(CalculationSession, UUID(session_c["session_id"]))
    assert calc_c is not None

    read_c = build_calculation_session_read(db_session, calc_c)
    assert read_c.step2 is not None
    assert read_c.step2.works[0].scope == "Shared initial scope"
    assert read_c.step2.works[0].product_name == "Dishwasher"


def test_engineer_b_edits_scope_engineer_a_sees_update(db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(db_session, calc_a, Step2Snapshot(works=[_dishwasher_block(scope="Engineer A scope")]))
    db_session.commit()

    _patch_step2(db_session, calc_b, Step2Snapshot(works=[_dishwasher_block(scope="Engineer B updated scope")]))
    db_session.commit()

    read_a = build_calculation_session_read(db_session, calc_a)
    assert read_a.step2 is not None
    assert read_a.step2.works[0].scope == "Engineer B updated scope"
    assert read_a.shared_step2 is not None
    assert read_a.shared_step2.updated_by_name == "Other Engineer"


def test_add_work_shared_across_engineers(db_session):
    _, _, _, _, _, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(
        db_session,
        calc_a,
        Step2Snapshot(works=[_dishwasher_block(), _custom_block(custom_title="Second work item")]),
    )
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert len(read_b.step2.works) == 2
    assert read_b.step2.works[1].custom_title == "Second work item"


def test_delete_work_shared_across_engineers(db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(
        db_session,
        calc_a,
        Step2Snapshot(works=[_dishwasher_block(), _custom_block()]),
    )
    db_session.commit()

    _patch_step2(db_session, calc_b, Step2Snapshot(works=[_dishwasher_block()]))
    db_session.commit()

    read_a = build_calculation_session_read(db_session, calc_a)
    assert read_a.step2 is not None
    assert len(read_a.step2.works) == 1


@pytest.mark.asyncio
async def test_photos_under_correct_work_block(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, _, _, _, _, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(
        db_session,
        calc_a,
        Step2Snapshot(works=[_dishwasher_block(), _custom_block()]),
    )
    db_session.commit()

    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=1,
        actor=vitor,
    )
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert len(read_b.step2.works[0].attachments) == 0
    assert len(read_b.step2.works[1].attachments) == 1
    assert read_b.step2.works[1].attachments[0].id == uploaded.id


@patch("app.services.calculation_session_service.calculate_session")
def test_submit_uses_shared_step2(mock_calculate, db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(db_session, calc_a, Step2Snapshot(works=[_dishwasher_block(scope="Shared for submit")]))
    db_session.commit()

    calc_b.step2_snapshot = Step2Snapshot(
        works=[_dishwasher_block(scope="Personal stale scope")]
    ).model_dump(mode="json")
    db_session.commit()

    submit_session(
        db_session,
        session_id=calc_b.id,
        session_token=calc_b.session_token,
        step2=None,
    )
    db_session.commit()

    assert mock_calculate.called
    submitted_step2 = mock_calculate.call_args.kwargs.get("step2")
    assert submitted_step2 is not None
    assert submitted_step2.works[0].scope == "Shared for submit"


def test_unassigned_cannot_access_shared_snapshot(db_session):
    quote, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    outsider = _engineer_user(db_session, email="outsider.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    assert calc_a is not None
    _patch_step2(db_session, calc_a, Step2Snapshot(works=[_dishwasher_block()]))
    db_session.commit()

    assert user_can_access_quote_work_snapshot(
        db_session,
        user=outsider,
        quote_ref=quote.quote_ref,
        eworks_quote_id=quote.eworks_quote_id,
        synced_quote_id=quote.id,
    ) is False

    with pytest.raises(AppError) as exc:
        save_shared_step2(
            db_session,
            calc_a,
            Step2Snapshot(works=[_dishwasher_block(scope="Blocked")]),
            actor=outsider,
        )
    assert exc.value.code == "QUOTE_WORK_FORBIDDEN"


def test_legacy_session_seeds_shared_on_first_load(db_session):
    quote, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    assert calc_a is not None and calc_b is not None

    legacy_step2 = Step2Snapshot(works=[_dishwasher_block(scope="Legacy session scope")])
    calc_a.step2_snapshot = legacy_step2.model_dump(mode="json")
    calc_a.updated_at = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)
    calc_b.step2_snapshot = Step2Snapshot(works=[_dishwasher_block(scope="Older scope")]).model_dump(mode="json")
    calc_b.updated_at = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    db_session.commit()

    assert get_quote_work_snapshot(db_session, quote_ref=quote.quote_ref, eworks_quote_id=quote.eworks_quote_id) is None

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert read_b.step2.works[0].scope == "Legacy session scope"

    row = get_quote_work_snapshot(db_session, quote_ref=quote.quote_ref, eworks_quote_id=quote.eworks_quote_id)
    assert row is not None
    seeded = Step2Snapshot.model_validate(row.step2_snapshot)
    assert seeded.works[0].scope == "Legacy session scope"


def test_personal_session_ignored_once_shared_exists(db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(db_session, calc_a, Step2Snapshot(works=[_dishwasher_block(scope="Shared canonical scope")]))
    db_session.commit()

    calc_b.step2_snapshot = Step2Snapshot(
        works=[_dishwasher_block(scope="Personal stale scope")]
    ).model_dump(mode="json")
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert read_b.step2.works[0].scope == "Shared canonical scope"


def test_custom_scope_title_shared(db_session):
    _, _, _, _, _, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(
        db_session,
        calc_a,
        Step2Snapshot(works=[_custom_block(custom_title="Shared bespoke title", scope="Detailed custom scope")]),
    )
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert read_b.step2.works[0].is_custom_scope is True
    assert read_b.step2.works[0].custom_title == "Shared bespoke title"
    assert read_b.step2.works[0].scope == "Detailed custom scope"


@patch("app.services.calculation_session_service.calculate_session")
def test_engineer_b_submits_with_shared_product_without_reselecting(mock_calculate, db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    shared_block = _dishwasher_block(scope="Shared product scope")
    _patch_step2(db_session, calc_a, Step2Snapshot(works=[shared_block]))
    db_session.commit()

    calc_b.step2_snapshot = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="",
                selected_product_id=None,
                product_name="",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    ).model_dump(mode="json")
    db_session.commit()

    incoming = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="",
                selected_product_id=None,
                product_name="",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    submit_session(
        db_session,
        session_id=calc_b.id,
        session_token=calc_b.session_token,
        step2=incoming,
    )
    db_session.commit()

    assert mock_calculate.called
    submitted_step2 = mock_calculate.call_args.kwargs.get("step2")
    assert submitted_step2 is not None
    assert submitted_step2.works[0].selected_product_id == 42
    assert submitted_step2.works[0].product_name == "Dishwasher"
    assert submitted_step2.works[0].scope == "Shared product scope"


@patch("app.services.calculation_session_service.calculate_session")
def test_engineer_b_submits_with_shared_custom_scope(mock_calculate, db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(
        db_session,
        calc_a,
        Step2Snapshot(works=[_custom_block(custom_title="Shared bespoke title", scope="Detailed custom scope")]),
    )
    db_session.commit()

    incoming = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="",
                is_custom_scope=False,
                custom_title="",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    submit_session(
        db_session,
        session_id=calc_b.id,
        session_token=calc_b.session_token,
        step2=incoming,
    )
    db_session.commit()

    assert mock_calculate.called
    submitted_step2 = mock_calculate.call_args.kwargs.get("step2")
    assert submitted_step2 is not None
    assert submitted_step2.works[0].is_custom_scope is True
    assert submitted_step2.works[0].custom_title == "Shared bespoke title"
    assert submitted_step2.works[0].scope == "Detailed custom scope"


def _scope_only_block(**overrides) -> WorkBlockSnapshot:
    block = WorkBlockSnapshot(
        scope="Replace damaged kitchen tap and check pipework",
        engineers_required=True,
        engineers_needed=1,
        engineer_time_value=Decimal("1.5"),
    )
    return block.model_copy(update=overrides)


def test_shared_scope_only_normalized_to_custom_scope(db_session):
    _, _, _, _, _, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(
        db_session,
        calc_a,
        Step2Snapshot(works=[_scope_only_block()]),
    )
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert read_b.step2.works[0].is_custom_scope is True
    assert read_b.step2.works[0].custom_title == "Replace damaged kitchen tap and check pipework"
    assert read_b.step2.works[0].product_name == "Replace damaged kitchen tap and check pipework"


@patch("app.services.calculation_session_service.calculate_session")
def test_engineer_b_submits_with_shared_scope_only(mock_calculate, db_session):
    _, _, _, _, other, calc_a, calc_b = _start_sessions(db_session)
    _patch_step2(db_session, calc_a, Step2Snapshot(works=[_scope_only_block()]))
    db_session.commit()

    incoming = Step2Snapshot(
        works=[
            WorkBlockSnapshot(
                scope="",
                selected_product_id=None,
                product_name="",
                engineers_required=True,
                engineers_needed=1,
                engineer_time_value=Decimal("1.5"),
            )
        ]
    )
    submit_session(
        db_session,
        session_id=calc_b.id,
        session_token=calc_b.session_token,
        step2=incoming,
    )
    db_session.commit()

    assert mock_calculate.called
    submitted_step2 = mock_calculate.call_args.kwargs.get("step2")
    assert submitted_step2 is not None
    assert submitted_step2.works[0].is_custom_scope is True
    assert submitted_step2.works[0].custom_title == "Replace damaged kitchen tap and check pipework"
    assert submitted_step2.works[0].scope == "Replace damaged kitchen tap and check pipework"


def test_legacy_session_seeds_scope_only_as_custom_scope(db_session):
    quote, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    assert calc_a is not None and calc_b is not None

    legacy_step2 = Step2Snapshot(scope="Quote description scope from first engineer")
    calc_a.step2_snapshot = legacy_step2.model_dump(mode="json")
    calc_a.updated_at = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)
    calc_b.step2_snapshot = legacy_step2.model_dump(mode="json")
    calc_b.updated_at = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert read_b.step2.works[0].is_custom_scope is True
    assert read_b.step2.works[0].custom_title == "Quote description scope from first engineer"
