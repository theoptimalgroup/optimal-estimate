"""Unit tests for shared quote work block attachments."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.types import AuthenticatedUser
from app.core.security import UserRole, get_password_hash
from app.db.session import get_db
from app.main import app
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
from app.schemas.eworks_link import SessionAttachmentMeta, Step2Snapshot, WorkBlockSnapshot
from app.services.calculation_session_service import (
    add_session_attachment,
    build_calculation_session_read,
    submit_session,
)
from app.services.quote_assignment_service import start_assignment_estimate
from app.services.quote_work_attachment_service import (
    list_quote_work_attachments,
    merge_shared_attachments_into_step2,
    user_can_view_quote_attachment,
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
    session.add_all([vitor, other, outsider, manager, trade, rule])
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def api_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


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


def _manager_user(db_session) -> AuthenticatedUser:
    user = db_session.query(User).filter(User.email == "manager@theoptimalgroup.co.uk").one()
    return AuthenticatedUser(
        id=str(user.id),
        email=user.email,
        name=user.full_name,
        role=UserRole.MANAGER,
        is_active=True,
        auth_provider="dev",
    )


def _seed_quote_with_assignments(db_session):
    quote = EworksQuote(
        eworks_quote_id=22143,
        quote_ref="Q22143",
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


def _make_upload(content: bytes = b"fake-image-bytes", filename: str = "photo.jpg") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": "image/jpeg"})


def _valid_work_block(**overrides) -> WorkBlockSnapshot:
    block = WorkBlockSnapshot(
        scope="Supply and fit materials as scoped.",
        is_custom_scope=True,
        custom_title="Custom scope",
    )
    return block.model_copy(update=overrides)


def _dishwasher_work_block(**overrides) -> WorkBlockSnapshot:
    block = WorkBlockSnapshot(
        scope="Repair dishwasher",
        selected_product_id=42,
        product_name="Dishwasher",
        product_code="DW-001",
        is_custom_scope=False,
    )
    return block.model_copy(update=overrides)


@pytest.mark.asyncio
async def test_engineer_a_upload_visible_to_engineer_b(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    assert calc_a is not None and calc_b is not None

    step2 = Step2Snapshot(works=[_valid_work_block()])
    calc_a.step2_snapshot = step2.model_dump(mode="json")
    calc_b.step2_snapshot = step2.model_dump(mode="json")
    db_session.commit()

    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    shared = list_quote_work_attachments(db_session, quote_ref="Q22143", eworks_quote_id=22143, work_index=0)
    assert len(shared) == 1
    assert shared[0].uploaded_by_name == "Vitor Espirito Santo"
    assert shared[0].attachment_id == uploaded.id

    read_b = build_calculation_session_read(db_session, calc_b)
    assert read_b.step2 is not None
    assert len(read_b.step2.works[0].attachments) == 1
    assert read_b.step2.works[0].attachments[0].id == uploaded.id
    assert read_b.step2.works[0].attachments[0].uploaded_by_name == "Vitor Espirito Santo"


@pytest.mark.asyncio
async def test_outsider_engineer_cannot_view_shared_attachment(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    outsider = _engineer_user(db_session, email="outsider.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(works=[_valid_work_block()]).model_dump(mode="json")
    db_session.commit()

    await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    row = list_quote_work_attachments(db_session, quote_ref="Q22143", eworks_quote_id=22143)[0]
    assert user_can_view_quote_attachment(db_session, user=outsider, attachment=row, session=None) is False


def test_manager_can_view_shared_attachment(db_session):
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    row = QuoteWorkAttachment(
        attachment_id="att-1",
        quote_ref="Q22143",
        eworks_quote_id=22143,
        synced_quote_id=assignment_a.synced_quote_id,
        work_index=0,
        file_name="photo.jpg",
        content_type="image/jpeg",
        size=10,
        media_type="photo",
        stored_name="att-1_photo.jpg",
        uploaded_by_name="Vitor Espirito Santo",
    )
    db_session.add(row)
    db_session.commit()

    manager = _manager_user(db_session)
    assert user_can_view_quote_attachment(db_session, user=manager, attachment=row, session=None) is True


@pytest.mark.asyncio
async def test_no_duplicates_on_reload(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    step2 = Step2Snapshot(works=[_valid_work_block()])
    calc_a.step2_snapshot = step2.model_dump(mode="json")
    calc_b.step2_snapshot = step2.model_dump(mode="json")
    db_session.commit()

    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    calc_b.step2_snapshot = Step2Snapshot(
        works=[_valid_work_block(attachments=[uploaded])]
    ).model_dump(mode="json")
    db_session.commit()

    merged = merge_shared_attachments_into_step2(
        db_session,
        calc_b,
        Step2Snapshot.model_validate(calc_b.step2_snapshot),
    )
    assert len(merged.works[0].attachments) == 1


@pytest.mark.asyncio
async def test_backward_compat_session_only_attachment(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    legacy = SessionAttachmentMeta(
        id="legacy-att-1",
        file_name="legacy.jpg",
        content_type="image/jpeg",
        size=12,
        media_type="photo",
        stored_name="legacy-att-1_legacy.jpg",
    )
    (tmp_path / str(calc_a.id)).mkdir(parents=True)
    (tmp_path / str(calc_a.id) / legacy.stored_name).write_bytes(b"legacy-bytes")

    calc_a.step2_snapshot = Step2Snapshot(
        works=[_valid_work_block(attachments=[legacy])]
    ).model_dump(mode="json")
    db_session.commit()

    read = build_calculation_session_read(db_session, calc_a)
    assert len(read.step2.works[0].attachments) == 1

    from app.services.quote_work_attachment_service import resolve_attachment_meta

    meta, row, _ = resolve_attachment_meta(db_session, calc_a.id, legacy.id)
    assert meta.file_name == "legacy.jpg"
    assert row is not None


@pytest.mark.asyncio
@patch("app.services.calculation_session_service.complete_revision_submit")
@patch("app.services.calculation_session_service.calculate_session")
async def test_submitted_estimate_includes_shared_media(mock_calculate, mock_complete_revision, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(works=[_valid_work_block()]).model_dump(mode="json")
    db_session.commit()

    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    captured: dict = {}

    def _capture_calculate(db, *, session_id, session_token, step2=None, idempotency_key=None):
        captured["step2"] = step2
        return None

    mock_calculate.side_effect = _capture_calculate
    mock_complete_revision.return_value = None

    submit_session(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        step2=Step2Snapshot(works=[_valid_work_block()]),
    )

    assert captured["step2"] is not None
    assert len(captured["step2"].works[0].attachments) == 1
    assert captured["step2"].works[0].attachments[0].id == uploaded.id


@pytest.mark.asyncio
async def test_upload_with_product_stores_product_name_and_scope_snapshot(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(works=[_dishwasher_work_block()]).model_dump(mode="json")
    db_session.commit()

    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    assert uploaded.product_name == "Dishwasher"
    assert uploaded.scope_snapshot == "Repair dishwasher"
    assert uploaded.product_id == 42
    assert uploaded.is_custom_scope is False

    row = list_quote_work_attachments(db_session, quote_ref="Q22143", eworks_quote_id=22143)[0]
    assert row.product_name == "Dishwasher"
    assert row.scope_snapshot == "Repair dishwasher"


@pytest.mark.asyncio
async def test_engineer_b_sees_shared_media_with_product_scope_context(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    step2 = Step2Snapshot(works=[_dishwasher_work_block()])
    calc_a.step2_snapshot = step2.model_dump(mode="json")
    calc_b.step2_snapshot = step2.model_dump(mode="json")
    db_session.commit()

    await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    attachment = read_b.step2.works[0].attachments[0]
    assert attachment.product_name == "Dishwasher"
    assert attachment.scope_snapshot == "Repair dishwasher"
    assert attachment.uploaded_by_name == "Vitor Espirito Santo"


@pytest.mark.asyncio
async def test_custom_scope_upload_stores_custom_scope_title(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(
        works=[
            _valid_work_block(
                is_custom_scope=True,
                custom_title="Bathroom leak investigation",
                scope="Investigate leak under bath.",
            )
        ]
    ).model_dump(mode="json")
    db_session.commit()

    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    assert uploaded.is_custom_scope is True
    assert uploaded.custom_scope_title == "Bathroom leak investigation"
    assert uploaded.product_name == "Bathroom leak investigation"


@pytest.mark.asyncio
async def test_custom_scope_visible_to_another_engineer(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    custom_block = _valid_work_block(
        is_custom_scope=True,
        custom_title="Bathroom leak investigation",
        scope="Investigate leak under bath.",
    )
    calc_a.step2_snapshot = Step2Snapshot(works=[custom_block]).model_dump(mode="json")
    calc_b.step2_snapshot = Step2Snapshot(works=[custom_block]).model_dump(mode="json")
    db_session.commit()

    await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    attachment = read_b.step2.works[0].attachments[0]
    assert attachment.is_custom_scope is True
    assert attachment.custom_scope_title == "Bathroom leak investigation"


@pytest.mark.asyncio
async def test_product_scope_change_keeps_original_attachment_context(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, assignment_b = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    other = _engineer_user(db_session, email="other.engineer@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    session_b = start_assignment_estimate(db_session, assignment_b.id, other)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_b = db_session.get(CalculationSession, UUID(session_b["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(works=[_dishwasher_work_block()]).model_dump(mode="json")
    db_session.commit()

    await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    calc_b.step2_snapshot = Step2Snapshot(
        works=[_dishwasher_work_block(product_name="Washing Machine", scope="Replace drum")]
    ).model_dump(mode="json")
    db_session.commit()

    read_b = build_calculation_session_read(db_session, calc_b)
    attachment = read_b.step2.works[0].attachments[0]
    assert attachment.product_name == "Dishwasher"
    assert attachment.scope_snapshot == "Repair dishwasher"


@pytest.mark.asyncio
async def test_legacy_backfill_includes_product_scope_when_available(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    from app.services.quote_work_attachment_service import register_legacy_attachment

    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()

    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    legacy = SessionAttachmentMeta(
        id="legacy-att-2",
        file_name="legacy.jpg",
        content_type="image/jpeg",
        size=12,
        media_type="photo",
        stored_name="legacy-att-2_legacy.jpg",
    )
    calc_a.step2_snapshot = Step2Snapshot(works=[_dishwasher_work_block(attachments=[legacy])]).model_dump(mode="json")
    db_session.commit()

    row = register_legacy_attachment(
        db_session,
        session=calc_a,
        work_index=0,
        attachment=legacy,
        actor=vitor,
    )
    db_session.commit()

    assert row is not None
    assert row.product_name == "Dishwasher"
    assert row.scope_snapshot == "Repair dishwasher"


@pytest.mark.asyncio
async def test_upload_with_work_block_context_always_has_product_name(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.eworks_attachment_service.settings.eworks_attachment_path", str(tmp_path))
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")

    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(works=[_dishwasher_work_block()]).model_dump(mode="json")
    db_session.commit()

    uploaded = await add_session_attachment(
        db_session,
        session_id=calc_a.id,
        session_token=calc_a.session_token,
        upload=_make_upload(),
        work_index=0,
        actor=vitor,
    )
    db_session.commit()

    assert uploaded.product_name
    read = build_calculation_session_read(db_session, calc_a)
    assert read.step2.works[0].attachments[0].product_name == "Dishwasher"


def test_unmatched_media_collected_when_work_index_missing(db_session):
    _, assignment_a, _ = _seed_quote_with_assignments(db_session)
    vitor = _engineer_user(db_session, email="vitor.santo@theoptimalgroup.co.uk")
    session_a = start_assignment_estimate(db_session, assignment_a.id, vitor)
    db_session.commit()
    calc_a = db_session.get(CalculationSession, UUID(session_a["session_id"]))
    calc_a.step2_snapshot = Step2Snapshot(works=[_dishwasher_work_block()]).model_dump(mode="json")
    db_session.commit()

    row = QuoteWorkAttachment(
        attachment_id="att-unmatched",
        quote_ref="Q22143",
        eworks_quote_id=22143,
        synced_quote_id=assignment_a.synced_quote_id,
        work_index=5,
        file_name="orphan.jpg",
        content_type="image/jpeg",
        size=10,
        media_type="photo",
        stored_name="att-unmatched_orphan.jpg",
        product_name="Dishwasher",
        scope_snapshot="Repair dishwasher",
    )
    db_session.add(row)
    db_session.commit()

    merged = merge_shared_attachments_into_step2(
        db_session,
        calc_a,
        Step2Snapshot.model_validate(calc_a.step2_snapshot),
    )
    assert len(merged.works[0].attachments) == 0
    assert len(merged.unmatched_attachments) == 1
    assert merged.unmatched_attachments[0].product_name == "Dishwasher"
