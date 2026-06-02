"""Integration tests for eWorks calculation session link flow."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.client_alias import ClientAlias
from app.models.rate_rule import RateRule
from app.models.trade import Trade
from tests.helpers.internal_notes import extract_core_internal_notes, normalize_internal_notes_for_test
from tests.test_db import make_test_session

ROOT = Path(__file__).resolve().parents[2]
ALEX_ROW_11_NOTES_PATH = ROOT / "tests" / "fixtures" / "alex_row_11_internal_notes.txt"
TEST_SECRET = "test-eworks-secret"
CURRENCY_TOLERANCE = Decimal("1")
PCT_TOLERANCE = Decimal("1")


def make_signed_payload(payload: dict, *, secret: str = TEST_SECRET) -> tuple[str, str]:
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return raw, sig


def _future_expiry(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _past_expiry() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _base_payload(**overrides) -> dict:
    payload = {
        "source": "eworks",
        "quote_number": "Q-123",
        "job_number": "JOB-456",
        "client": "Lambert Chartered Surveyors",
        "trade": "Carpenter",
        "property_address": "The Factory, 1 Nile Street",
        "congestion_required": True,
        "congestion_amount": 18,
        "travel": 0,
        "expires_at": _future_expiry(),
    }
    payload.update(overrides)
    return payload


def _make_lambert_carpenter_rule(client_id, trade_id) -> RateRule:
    return RateRule(
        client_id=client_id,
        trade_id=trade_id,
        formula_source="xlsx",
        version="alex-xlsx-test",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0"),
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
        xlsx_client_name="Lambert Chartered Surveyors",
        xlsx_trade_name="Carpenter",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )


def _make_lambert_plumber_rule(client_id, trade_id) -> RateRule:
    return RateRule(
        client_id=client_id,
        trade_id=trade_id,
        formula_source="xlsx",
        version="plumber-xlsx-test",
        hourly_rate=Decimal("120"),
        day_rate=Decimal("300"),
        direct_hourly_cost=Decimal("40"),
        direct_daily_cost=Decimal("300"),
        client_fee_pct=Decimal("0"),
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
        xlsx_client_name="Lambert Chartered Surveyors",
        xlsx_trade_name="Plumber",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )


@pytest.fixture()
def eworks_api_client(monkeypatch):
    monkeypatch.setattr(settings, "eworks_link_secret", TEST_SECRET)
    monkeypatch.setattr(settings, "eworks_link_sig_required", True)

    session, _ = make_test_session()
    client = Client(id=uuid.uuid4(), name="Lamberts Chartered Surveyors", default_vat_rate=Decimal("20"))
    alias = ClientAlias(id=uuid.uuid4(), client_id=client.id, alias_name="Lambert Chartered Surveyors")
    trade = Trade(id=uuid.uuid4(), name="Carpenter")
    plumber_trade = Trade(id=uuid.uuid4(), name="Plumber")
    rule = _make_lambert_carpenter_rule(client.id, trade.id)
    plumber_rule = _make_lambert_plumber_rule(client.id, plumber_trade.id)
    session.add_all([client, alias, trade, plumber_trade, rule, plumber_rule])
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, session
    app.dependency_overrides.clear()
    session.close()


def _from_link(test_client: TestClient, payload: dict, sig: str | None = None):
    raw, expected_sig = make_signed_payload(payload)
    return test_client.post(
        "/api/v1/calculation-session/from-link",
        json={"payload": raw, "sig": sig if sig is not None else expected_sig},
    )


def test_from_link_populates_step1(eworks_api_client):
    test_client, _ = eworks_api_client
    response = _from_link(test_client, _base_payload())
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"]
    assert data["session_token"]
    assert data["step1"]["job_number"] == "JOB-456"
    assert data["step1"]["client_name"] == "Lamberts Chartered Surveyors"
    assert data["step1"]["trade_name"] == "Carpenter"
    assert data["resolved"]["formula_source"] == "xlsx"
    assert data["resolved"]["xlsx_client_name"] == "Lambert Chartered Surveyors"
    assert data["resumed"] is False


def test_from_link_resumes_existing_session_with_progress(eworks_api_client):
    test_client, _ = eworks_api_client
    payload = _base_payload(quote_number="Q-RESUME-001", job_number="JOB-RESUME-001")
    first = _from_link(test_client, payload).json()["data"]
    session_id = first["session_id"]
    token = first["session_token"]

    step2 = _alex_row_11_step2(findings="Saved progress findings.")
    patch = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={
            "step2": step2,
            "ui_state": {"current_step": 2, "max_reachable_step": 2, "last_result": None},
        },
    )
    assert patch.status_code == 200

    second = _from_link(test_client, payload).json()["data"]
    assert second["resumed"] is True
    assert second["session_id"] == session_id
    assert second["session_token"] == token
    assert second["ui_state"]["current_step"] == 2
    assert second["ui_state"]["max_reachable_step"] == 2
    assert second["step2"]["findings"] == "Saved progress findings."


def test_from_link_builds_quote_description_from_pdf_fields(eworks_api_client):
    test_client, _ = eworks_api_client
    response = _from_link(
        test_client,
        _base_payload(
            access_notes="Meet caretaker on site at 8am",
            original_job_description="Please provide a quote for door upgrades",
            booked_by="Billie",
            travel_notes="1st appt",
            contact="Alex - 07960696064",
            quote_screening_answers="1. No pictures.\n2. ASAP",
            congestion_required=True,
        ),
    )
    assert response.status_code == 200
    description = response.json()["data"]["step1"]["quote_description"]
    assert "Access: Meet caretaker on site at 8am" in description
    assert "Quote: Please provide a quote for door upgrades" in description
    assert "Info: Booked by Billie" in description
    assert "Travel: 1st appt" in description
    assert "Quote Screening Answers:" in description


def test_missing_payload_returns_400(eworks_api_client):
    test_client, _ = eworks_api_client
    response = test_client.post("/api/v1/calculation-session/from-link", json={"payload": "", "sig": "abc"})
    assert response.status_code == 400
    assert "Missing calculation link payload" in response.json()["detail"]


def test_invalid_payload_returns_400(eworks_api_client):
    test_client, _ = eworks_api_client
    response = test_client.post("/api/v1/calculation-session/from-link", json={"payload": "not-valid!!!", "sig": "abc"})
    assert response.status_code == 400
    assert "Invalid calculation link payload" in response.json()["detail"]


def test_raw_json_payload_accepted_when_sig_not_required(monkeypatch):
    monkeypatch.setattr(settings, "eworks_link_sig_required", False)
    session, _ = make_test_session()
    client = Client(id=uuid.uuid4(), name="Lamberts Chartered Surveyors", default_vat_rate=Decimal("20"))
    alias = ClientAlias(id=uuid.uuid4(), client_id=client.id, alias_name="Lambert Chartered Surveyors")
    trade = Trade(id=uuid.uuid4(), name="Carpenter")
    rule = _make_lambert_carpenter_rule(client.id, trade.id)
    session.add_all([client, alias, trade, rule])
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    payload = _base_payload()
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/calculation-session/from-link",
            json={"payload": json.dumps(payload), "sig": None},
        )
        assert response.status_code == 200
        assert response.json()["data"]["step1"]["job_number"] == "JOB-456"
    app.dependency_overrides.clear()
    session.close()


def test_missing_required_fields_returns_clear_error(eworks_api_client):
    test_client, _ = eworks_api_client
    raw = base64.urlsafe_b64encode(json.dumps({"client": "Lambert Chartered Surveyors"}).encode()).decode()
    response = test_client.post("/api/v1/calculation-session/from-link", json={"payload": raw, "sig": "abc"})
    assert response.status_code == 400
    assert "missing required fields" in response.json()["detail"].lower()


def test_invalid_signature_returns_401(eworks_api_client):
    test_client, _ = eworks_api_client
    raw, _ = make_signed_payload(_base_payload())
    response = test_client.post("/api/v1/calculation-session/from-link", json={"payload": raw, "sig": "bad-signature"})
    assert response.status_code == 401
    assert "Invalid link signature" in response.json()["detail"]


def test_expired_payload_returns_410(eworks_api_client):
    test_client, _ = eworks_api_client
    response = _from_link(test_client, _base_payload(expires_at=_past_expiry()))
    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()


def test_patch_stores_findings(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    step2 = {
        "findings": "Damaged architrave noted on site.",
        "scope": "Replace architrave and make good.",
        "labour_type": "hourly",
        "engineers": 1,
        "hours": 1.5,
        "days": 0,
        "labourer_days": 0,
        "material_name": "Materials",
        "quantity": 1,
        "unit_cost": 190,
        "markup_value": 20,
        "parking_required": False,
        "congestion_required": True,
        "congestion_amount": 18,
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.patch(
        f"/api/v1/calculation-session/{created['session_id']}",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["step2"]["findings"] == step2["findings"]


def _alex_row_11_step2(**overrides) -> dict:
    step2 = {
        "findings": "Site visit complete.",
        "scope": "Supply and fit materials as scoped.",
        "labour_type": "hourly",
        "engineers": 1,
        "hours": 1.5,
        "days": 0,
        "labourer_days": 0,
        "material_name": "Materials",
        "quantity": 1,
        "unit_cost": 190,
        "markup_value": 20,
        "parking_required": False,
        "congestion_required": True,
        "congestion_amount": 18,
        "travel_charge": 0,
        "other_charge": 0,
    }
    step2.update(overrides)
    return step2


def _alex_work_block(**overrides) -> dict:
    block = {
        "scope": "Supply and fit materials as scoped.",
        "materials_to_order": [{"link": "", "quantity": 1, "cost": 190}],
        "shelf_materials_cost": 0,
        "skill_required": "Carpenter",
        "engineers_required": True,
        "engineers_needed": 1,
        "engineer_time_unit": "hours",
        "engineer_time_value": 1.5,
        "labour_required": False,
        "labour_needed": 0,
        "labour_time_value": 1,
        "markup_value": 20,
        "labour_type": "hourly",
        "engineers": 1,
        "hours": 1.5,
        "quantity": 1,
        "unit_cost": 190,
    }
    block.update(overrides)
    return block


def test_calculate_alex_row_11_parity(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    step2 = _alex_row_11_step2()
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    breakdown = data["breakdown"]
    assert breakdown["formula_source"] == "xlsx"
    assert abs(Decimal(str(breakdown["labour_charge_to_client"])) - Decimal("145")) <= CURRENCY_TOLERANCE
    assert abs(Decimal(str(breakdown["materials_parking_cc_charge"])) - Decimal("260")) <= CURRENCY_TOLERANCE
    assert abs(Decimal(str(breakdown["profit_gbp"])) - Decimal("153")) <= CURRENCY_TOLERANCE
    assert abs(Decimal(str(breakdown["profit_pct"])) - Decimal("38")) <= PCT_TOLERANCE

    expected_notes = normalize_internal_notes_for_test(ALEX_ROW_11_NOTES_PATH.read_text(encoding="utf-8"))
    actual_notes = normalize_internal_notes_for_test(data["internal_notes"])
    assert extract_core_internal_notes(actual_notes) == extract_core_internal_notes(expected_notes)

    client_calc = data["client_view"]["calculation"]
    assert "internal_notes" not in client_calc
    assert "profit_gbp" not in client_calc
    assert "profit_pct" not in client_calc
    assert "direct_labour_cost" not in client_calc


def test_legacy_flat_step2_still_calculates(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": _alex_row_11_step2()},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["work_breakdowns"]) == 1
    assert data["work_breakdowns"][0]["work_index"] == 0


def test_two_work_session_combined_total(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    three_hour = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={
            "step2": {
                "works": [
                    _alex_work_block(
                        scope="Single 3h work with combined materials",
                        engineer_time_value=3,
                        hours=3,
                        materials_to_order=[{"link": "", "quantity": 1, "cost": 380}],
                        unit_cost=380,
                    ),
                ],
                "parking_required": False,
                "congestion_required": True,
                "congestion_amount": 18,
                "travel_charge": 0,
                "other_charge": 0,
            }
        },
    ).json()["data"]
    combined_baseline = three_hour["breakdown"]

    step2 = {
        "works": [
            _alex_work_block(scope="Work one scope"),
            _alex_work_block(scope="Work two scope"),
        ],
        "parking_required": False,
        "congestion_required": True,
        "congestion_amount": 18,
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["work_breakdowns"]) == 2
    breakdown = data["breakdown"]
    assert abs(
        Decimal(str(breakdown["labour_charge_to_client"]))
        - Decimal(str(combined_baseline["labour_charge_to_client"]))
    ) <= CURRENCY_TOLERANCE
    assert abs(
        Decimal(str(breakdown["materials_parking_cc_charge"]))
        - Decimal(str(combined_baseline["materials_parking_cc_charge"]))
    ) <= CURRENCY_TOLERANCE
    assert abs(
        Decimal(str(breakdown["profit_gbp"]))
        - Decimal(str(combined_baseline["profit_gbp"]))
    ) <= CURRENCY_TOLERANCE
    assert data.get("aggregated_summary") is not None
    assert data["aggregated_summary"]["subtitle"] == "3 hours total across 2 works"
    assert data["work_breakdowns"][0]["breakdown"]["labour_charge_to_client"] != breakdown["labour_charge_to_client"]


def test_single_work_includes_session_charges_in_internal_notes(eworks_api_client):
    """1 carpenter × 2h with £100 materials, £100 parking, £100 CC — matches XLSX helper."""
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(congestion_required=False, congestion_amount=0)).json()["data"]
    step2 = {
        "works": [
            _alex_work_block(
                scope="Lambert job",
                engineer_time_value=2,
                hours=2,
                materials_to_order=[{"link": "", "quantity": 1, "cost": 100}],
                unit_cost=100,
                quantity=1,
                parking_required=True,
                parking_type="fixed",
                parking_fixed_amount=100,
                congestion_required=True,
                congestion_amount=100,
            ),
        ],
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    notes = normalize_internal_notes_for_test(data["internal_notes"])
    assert "Carpenter" in notes and "2" in notes and "Hour/s" in notes
    assert "BUDGET: Materials: £100 / Parking: £100 / CC: £100" in notes
    assert "TOTAL COST TO OPTIMAL: Labour etc: £58 / Materials etc: £300" in notes
    assert "TOTAL CHARGE TO CLIENT: Labour: £190 / Materials etc: £375" in notes
    assert "PROFIT ON JOB: £207 / 37%" in notes
    assert "EXTERNAL DELIVERY:" in notes
    assert "Labour Only:" in notes and "@ £" in notes and "p/h" in notes
    assert "Labour & Materials:" in notes

    breakdown = data["breakdown"]
    assert abs(Decimal(str(breakdown["labour_charge_to_client"])) - Decimal("190")) <= CURRENCY_TOLERANCE
    assert abs(Decimal(str(breakdown["materials_parking_cc_charge"])) - Decimal("375")) <= CURRENCY_TOLERANCE
    assert abs(Decimal(str(breakdown["profit_gbp"])) - Decimal("207")) <= CURRENCY_TOLERANCE
    assert abs(Decimal(str(breakdown["profit_pct"])) - Decimal("37")) <= PCT_TOLERANCE


def test_calculate_persists_ui_state(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": _alex_row_11_step2()},
    )
    assert response.status_code == 200

    session_data = test_client.get(
        f"/api/v1/calculation-session/{created['session_id']}",
        headers={"X-Session-Token": created["session_token"]},
    ).json()["data"]
    assert session_data["ui_state"]["current_step"] == 3
    assert session_data["ui_state"]["max_reachable_step"] == 3
    assert session_data["ui_state"]["last_result"]["breakdown"]["final_total"] is not None


def test_session_pdf_download(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    headers = {"X-Session-Token": token}

    test_client.post(
        f"/api/v1/calculation-session/{session_id}/calculate",
        headers=headers,
        json={"step2": _alex_row_11_step2()},
    )

    pdf_response = test_client.post(
        f"/api/v1/calculation-session/{session_id}/pdf",
        headers=headers,
        json={"is_draft": False},
    )
    assert pdf_response.status_code == 200
    assert "attachment" in pdf_response.headers.get("content-disposition", "")
    assert pdf_response.headers.get("content-type") in {"application/pdf", "text/html; charset=utf-8"}
    assert len(pdf_response.content) > 100
    if pdf_response.headers.get("content-type") == "application/pdf":
        assert pdf_response.content.startswith(b"%PDF")
    else:
        body = pdf_response.content.decode("utf-8")
        assert "Lambert" in body or "Lamberts" in body
        assert "-- 1 of" in body
        assert "Combined Quote" in body
        assert "Internal Notes (Combined)" in body
        assert "BUDGET:" in body


def test_attachment_upload_targets_work_index(eworks_api_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "eworks_attachment_path", str(tmp_path))
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]

    step2 = {
        "works": [
            _alex_work_block(scope="Work one"),
            _alex_work_block(scope="Work two"),
        ],
        "congestion_required": True,
        "congestion_amount": 18,
    }
    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )

    response = test_client.post(
        f"/api/v1/calculation-session/{session_id}/attachments?work_index=1",
        headers={"X-Session-Token": token},
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    attachment = response.json()["data"]
    assert attachment["file_name"] == "photo.jpg"

    session_data = test_client.get(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
    ).json()["data"]
    works = session_data["step2"]["works"]
    assert len(works[0]["attachments"]) == 0
    assert len(works[1]["attachments"]) == 1
    assert works[1]["attachments"][0]["file_name"] == "photo.jpg"


def test_attachment_view_and_delete(eworks_api_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "eworks_attachment_path", str(tmp_path))
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]

    step2 = {"works": [_alex_work_block(scope="Work one")]}
    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )

    upload = test_client.post(
        f"/api/v1/calculation-session/{session_id}/attachments?work_index=0",
        headers={"X-Session-Token": token},
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert upload.status_code == 200
    attachment_id = upload.json()["data"]["id"]

    view = test_client.get(
        f"/api/v1/calculation-session/{session_id}/attachments/{attachment_id}?token={token}",
    )
    assert view.status_code == 200
    assert view.content == b"fake-image-bytes"
    assert view.headers.get("content-type") == "image/jpeg"

    delete = test_client.delete(
        f"/api/v1/calculation-session/{session_id}/attachments/{attachment_id}",
        headers={"X-Session-Token": token},
    )
    assert delete.status_code == 204

    session_data = test_client.get(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
    ).json()["data"]
    assert session_data["step2"]["works"][0]["attachments"] == []

    missing = test_client.get(
        f"/api/v1/calculation-session/{session_id}/attachments/{attachment_id}?token={token}",
    )
    assert missing.status_code == 404


def test_submit_marks_session_and_lists_on_dashboard(eworks_api_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "eworks_attachment_path", str(tmp_path))
    monkeypatch.setattr(settings, "dashboard_password", "test-dashboard-pass")
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-SUBMIT", job_number="JOB-SUBMIT")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {"works": [_alex_work_block(scope="Submitted work")], "congestion_required": True, "congestion_amount": 18}
    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )

    unauthorized = test_client.get("/api/v1/dashboard/quotes")
    assert unauthorized.status_code == 401

    upload = test_client.post(
        f"/api/v1/calculation-session/{session_id}/attachments?work_index=0",
        headers={"X-Session-Token": token},
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert upload.status_code == 200

    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200
    assert submit.json()["data"]["submitted"] is True

    dashboard = test_client.get(
        "/api/v1/dashboard/quotes",
        headers={"X-Dashboard-Password": "test-dashboard-pass"},
    )
    assert dashboard.status_code == 200
    quotes = dashboard.json()["data"]["quotes"]
    quote = next(item for item in quotes if item["quote_number"] == "Q-SUBMIT")
    assert quote["job_number"] == "JOB-SUBMIT"
    assert quote["works"][0]["scope"] == "Submitted work"
    assert quote["works"][0]["details"]["scope"] == "Submitted work"
    assert quote["works"][0]["attachments"][0]["file_name"] == "photo.jpg"
    assert quote["final_total"] is not None


def test_dashboard_reopen_quote_for_refill(eworks_api_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "dashboard_password", "test-dashboard-pass")
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-REOPEN", job_number="JOB-REOPEN")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {"works": [_alex_work_block(scope="Before reopen")], "congestion_required": True, "congestion_amount": 18}

    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200

    reopen = test_client.post(
        f"/api/v1/dashboard/quotes/{session_id}/reopen",
        headers={"X-Dashboard-Password": "test-dashboard-pass"},
    )
    assert reopen.status_code == 200
    reopened = reopen.json()["data"]
    assert reopened["session_id"] == session_id
    assert reopened["session_token"] == token

    get_session = test_client.get(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
    )
    assert get_session.status_code == 200
    ui_state = get_session.json()["data"]["ui_state"]
    assert ui_state["current_step"] == 1
    assert ui_state["last_result"] is None

    patch = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": {"works": [_alex_work_block(scope="After reopen")]}},
    )
    assert patch.status_code == 200


def test_dashboard_recalculates_when_last_result_missing(eworks_api_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "dashboard_password", "test-dashboard-pass")
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-RECALC", job_number="JOB-RECALC")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {"works": [_alex_work_block(scope="Recalc scope")], "congestion_required": True, "congestion_amount": 18}

    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200

    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"ui_state": {"current_step": 1, "max_reachable_step": 1}},
    )

    dashboard = test_client.get(
        "/api/v1/dashboard/quotes",
        headers={"X-Dashboard-Password": "test-dashboard-pass"},
    )
    assert dashboard.status_code == 200
    quote = next(item for item in dashboard.json()["data"]["quotes"] if item["quote_number"] == "Q-RECALC")
    assert quote["final_total"] is not None
    assert quote["works"][0]["labour_subtotal"] is not None
    assert quote["works"][0]["internal_notes"]


def test_dashboard_combine_notes_merges_same_trade_works(eworks_api_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "dashboard_password", "test-dashboard-pass")
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-COMBINE", job_number="JOB-COMBINE")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {
        "works": [
            _alex_work_block(scope="Work one", materials_to_order=[{"link": "Item", "quantity": 1, "cost": 100}]),
            _alex_work_block(scope="Work two", materials_to_order=[{"link": "Wsb", "quantity": 1, "cost": 10}]),
        ],
        "congestion_required": True,
        "congestion_amount": 18,
    }

    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200

    combine = test_client.post(
        f"/api/v1/dashboard/quotes/{session_id}/combine-notes",
        headers={"X-Dashboard-Password": "test-dashboard-pass"},
        json={"work_indexes": [0, 1]},
    )
    assert combine.status_code == 200
    notes = combine.json()["data"]["internal_notes"]
    assert notes.count("Enter this information into internal notes:") == 1
    assert "Item x 1" in notes
    assert "Wsb x 1" in notes
    assert "Work 1:" not in notes
    assert "Work 2:" not in notes


def test_dashboard_combined_pdf_download(eworks_api_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "dashboard_password", "test-dashboard-pass")
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-PDF", job_number="JOB-PDF")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {
        "works": [
            _alex_work_block(scope="PDF work one"),
            _alex_work_block(scope="PDF work two"),
        ],
        "congestion_required": True,
        "congestion_amount": 18,
    }

    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200

    for view_type in ("client", "optimal"):
        response = test_client.post(
            f"/api/v1/dashboard/quotes/{session_id}/combined-pdf",
            headers={"X-Dashboard-Password": "test-dashboard-pass"},
            json={"work_indexes": [0, 1], "view_type": view_type},
        )
        assert response.status_code == 200
        expected_stem = "Q-PDF_Client_view" if view_type == "client" else "Q-PDF_optimal_view"
        disposition = response.headers["content-disposition"]
        assert f'filename="{expected_stem}.pdf"' in disposition or f'filename="{expected_stem}.html"' in disposition
        assert response.headers["content-type"] in {"application/pdf", "text/html; charset=utf-8"}
        body = response.content
        assert len(body) > 100
        if response.headers["content-type"].startswith("text/html"):
            assert b"PDF work one" in body
            if view_type == "optimal":
                assert b"OPTIMAL QUOTE SUMMARY" in body
            else:
                assert b"QUOTE SUMMARY" in body


def test_patch_ui_state_preserves_last_result_after_submit(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-PATCH", job_number="JOB-PATCH")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {"works": [_alex_work_block(scope="Preserve result")], "congestion_required": True, "congestion_amount": 18}

    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200

    patch = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"ui_state": {"current_step": 2, "max_reachable_step": 2}},
    )
    assert patch.status_code == 200
    ui_state = patch.json()["data"]["ui_state"]
    assert ui_state["last_result"] is not None
    assert ui_state["last_result"]["breakdown"]["final_total"] is not None


def test_patch_step2_rejected_after_submit(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload(quote_number="Q-LOCK", job_number="JOB-LOCK")).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    step2 = {"works": [_alex_work_block(scope="Locked after submit")], "congestion_required": True, "congestion_amount": 18}

    submit = test_client.post(
        f"/api/v1/calculation-session/{session_id}/submit",
        headers={"X-Session-Token": token},
        json={"step2": step2},
    )
    assert submit.status_code == 200

    patch = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers={"X-Session-Token": token},
        json={"step2": {"works": [_alex_work_block(scope="Should not apply")]}},
    )
    assert patch.status_code == 409


def test_patch_replays_idempotent_response(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    body = {"step2": _alex_row_11_step2(findings="Idempotent findings.")}
    headers = {"X-Session-Token": token, "Idempotency-Key": "patch-test-key"}

    first = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers=headers,
        json=body,
    )
    assert first.status_code == 200
    assert first.json()["data"]["step2"]["findings"] == "Idempotent findings."

    second = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers=headers,
        json=body,
    )
    assert second.status_code == 200
    assert second.json()["data"]["step2"]["findings"] == "Idempotent findings."


def test_patch_idempotency_conflict_returns_409(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    headers = {"X-Session-Token": token, "Idempotency-Key": "patch-conflict-key"}

    test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers=headers,
        json={"step2": _alex_row_11_step2(findings="First body.")},
    )
    response = test_client.patch(
        f"/api/v1/calculation-session/{session_id}",
        headers=headers,
        json={"step2": _alex_row_11_step2(findings="Different body.")},
    )
    assert response.status_code == 409
    assert "different request body" in response.json()["detail"].lower()


def test_calculate_replays_idempotent_response(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    session_id = created["session_id"]
    token = created["session_token"]
    body = {"step2": _alex_row_11_step2()}
    headers = {"X-Session-Token": token, "Idempotency-Key": "calculate-test-key"}

    first = test_client.post(
        f"/api/v1/calculation-session/{session_id}/calculate",
        headers=headers,
        json=body,
    )
    assert first.status_code == 200
    first_total = first.json()["data"]["breakdown"]["final_total"]

    second = test_client.post(
        f"/api/v1/calculation-session/{session_id}/calculate",
        headers=headers,
        json=body,
    )
    assert second.status_code == 200
    assert second.json()["data"]["breakdown"]["final_total"] == first_total


def test_from_link_uses_stable_session_idempotency_key(eworks_api_client):
    test_client, _ = eworks_api_client
    payload = _base_payload(quote_number="Q-IDEM-001", job_number="JOB-IDEM-001")
    first = _from_link(test_client, payload)
    assert first.status_code == 200
    first_data = first.json()["data"]

    second = _from_link(test_client, payload)
    assert second.status_code == 200
    second_data = second.json()["data"]
    assert second_data["session_id"] == first_data["session_id"]
    assert second_data["session_token"] == first_data["session_token"]
    assert second_data["resumed"] is True


def test_calculate_uses_skill_required_trade_not_link_trade(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    carpenter = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": {"works": [_alex_work_block(skill_required="Carpenter")], "congestion_required": True, "congestion_amount": 18}},
    ).json()["data"]
    plumber = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": {"works": [_alex_work_block(skill_required="Plumber")], "congestion_required": True, "congestion_amount": 18}},
    ).json()["data"]

    carpenter_labour = Decimal(str(carpenter["breakdown"]["labour_charge_to_client"]))
    plumber_labour = Decimal(str(plumber["breakdown"]["labour_charge_to_client"]))
    assert abs(carpenter_labour - Decimal("145")) <= CURRENCY_TOLERANCE
    assert plumber_labour != carpenter_labour
    assert "Plumber" in (plumber["internal_notes"] or "")


def test_multi_work_same_skill_uses_selected_trade(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    step2 = {
        "works": [
            _alex_work_block(scope="Work one", skill_required="Plumber"),
            _alex_work_block(scope="Work two", skill_required="Plumber"),
        ],
        "congestion_required": True,
        "congestion_amount": 18,
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    plumber_single = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers={"X-Session-Token": created["session_token"]},
        json={"step2": {"works": [_alex_work_block(skill_required="Plumber")], "congestion_required": True, "congestion_amount": 18}},
    ).json()["data"]
    assert Decimal(str(data["breakdown"]["labour_charge_to_client"])) != Decimal(
        str(plumber_single["breakdown"]["labour_charge_to_client"])
    )
    assert "Plumber" in (data["internal_notes"] or "")


def test_multi_work_mixed_skills_combined_quote(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    headers = {"X-Session-Token": created["session_token"]}
    step2 = {
        "works": [
            _alex_work_block(scope="Work one", skill_required="Plumber"),
            _alex_work_block(scope="Work two", skill_required="Carpenter"),
        ],
        "congestion_required": True,
        "congestion_amount": 18,
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    summary = data["aggregated_summary"]
    assert summary["mixed_skills"] is True
    assert summary["skills"] == ["Plumber", "Carpenter"]
    assert "Plumber, Carpenter" in summary["subtitle"]

    plumber_only = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={"step2": {"works": [_alex_work_block(skill_required="Plumber")], "congestion_required": True, "congestion_amount": 18}},
    ).json()["data"]
    carpenter_only = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={"step2": {"works": [_alex_work_block(skill_required="Carpenter")], "congestion_required": True, "congestion_amount": 18}},
    ).json()["data"]
    expected_labour = Decimal(str(plumber_only["breakdown"]["labour_charge_to_client"])) + Decimal(
        str(carpenter_only["breakdown"]["labour_charge_to_client"])
    )
    assert abs(Decimal(str(data["breakdown"]["labour_charge_to_client"])) - expected_labour) <= CURRENCY_TOLERANCE
    assert "--- Plumber ---" in (data["internal_notes"] or "")
    assert "--- Carpenter ---" in (data["internal_notes"] or "")
    assert "BUDGET: Materials:" in (data["internal_notes"] or "")


def test_multi_work_mixed_skills_includes_parking_in_xlsx_materials_charge(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    headers = {"X-Session-Token": created["session_token"]}
    step2 = {
        "works": [
            _alex_work_block(
                scope="Work one",
                skill_required="Plumber",
                parking_required=True,
                parking_type="fixed",
                parking_fixed_amount=100,
                congestion_required=True,
                congestion_amount=18,
            ),
            _alex_work_block(
                scope="Work two",
                skill_required="Carpenter",
                congestion_required=True,
                congestion_amount=18,
            ),
        ],
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    breakdown = data["breakdown"]
    assert not any(line["label"] == "Parking" for line in breakdown.get("charges", []))
    assert "Parking: £100" in (data["internal_notes"] or "")
    assert Decimal(str(breakdown["materials_parking_cc_charge"])) > Decimal("380")


def test_mixed_skills_two_carpenter_one_plumber_groups_by_skill(eworks_api_client):
    test_client, _ = eworks_api_client
    created = _from_link(test_client, _base_payload()).json()["data"]
    headers = {"X-Session-Token": created["session_token"]}
    step2 = {
        "works": [
            _alex_work_block(scope="Carpenter work one", skill_required="Carpenter"),
            _alex_work_block(scope="Carpenter work two", skill_required="Carpenter"),
            _alex_work_block(scope="Plumber work", skill_required="Plumber"),
        ],
        "congestion_required": True,
        "congestion_amount": 18,
        "travel_charge": 0,
        "other_charge": 0,
    }
    response = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={"step2": step2},
    )
    assert response.status_code == 200
    data = response.json()["data"]

    carpenter_three_hour = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={
            "step2": {
                "works": [
                    _alex_work_block(
                        scope="Three hour carpenter",
                        skill_required="Carpenter",
                        engineer_time_value=3,
                        hours=3,
                    ),
                ],
                "congestion_required": True,
                "congestion_amount": 18,
            }
        },
    ).json()["data"]
    plumber_one_five = test_client.post(
        f"/api/v1/calculation-session/{created['session_id']}/calculate",
        headers=headers,
        json={"step2": {"works": [_alex_work_block(skill_required="Plumber")], "congestion_required": True, "congestion_amount": 18}},
    ).json()["data"]
    expected_labour = Decimal(str(carpenter_three_hour["breakdown"]["labour_charge_to_client"])) + Decimal(
        str(plumber_one_five["breakdown"]["labour_charge_to_client"])
    )
    assert abs(Decimal(str(data["breakdown"]["labour_charge_to_client"])) - expected_labour) <= CURRENCY_TOLERANCE


def test_dev_bootstrap_creates_session(eworks_api_client):
    test_client, _ = eworks_api_client
    response = test_client.post("/api/v1/calculation-session/dev-bootstrap")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"]
    assert data["step1"]["quote_number"] == "Q21863"
    assert data["step1"]["job_number"] == "33629"
