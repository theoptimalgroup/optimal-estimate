from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.engines.rules_engine import find_active_rule
from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.trade import Trade
from app.schemas.eworks_link import (
    CalculationSessionFromLinkResponse,
    EworksLinkPayload,
    ResolvedRuleInfo,
    SessionUiState,
    Step1Snapshot,
    Step2Snapshot,
    WorkBlockSnapshot,
)
from app.services.idempotency_service import (
    hash_payload,
    session_idempotency_key,
    store_idempotency,
)
from app.models.rate_rule import RateRule
from app.services.client_service import find_client_by_name_or_alias, get_or_create_client_for_import
from app.services.eworks_api_service import fetch_customer_by_name
from app.services.eworks_questionnaire_service import step2_from_link_questionnaire
from app.schemas.eworks_api import client_fee_pct_from_snapshot
from app.services.trade_service import normalize_trade_name


def _link_secret() -> str:
    return settings.eworks_link_secret or settings.secret_key


def _normalize_payload_string(payload_b64: str) -> str:
    """Normalize payload from URL query strings (spaces, padding, whitespace)."""
    raw = payload_b64.strip()
    # Browsers/form parsers often turn '+' into spaces in query strings.
    if " " in raw and "+" not in raw:
        raw = raw.replace(" ", "+")
    return raw


def _decode_payload_bytes(raw: str) -> dict:
    """Decode base64 (url-safe or standard) or raw JSON into a dict."""
    stripped = raw.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    normalized = _normalize_payload_string(stripped)
    padding = "=" * (-len(normalized) % 4)
    padded = normalized + padding
    last_error: Exception | None = None
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(padded)
            return json.loads(decoded.decode("utf-8"))
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
            last_error = exc
            continue
    hint = ""
    if len(stripped) < 80 or stripped.endswith("...") or "..." in stripped:
        hint = " (link looks truncated — copy the full URL from generate_eworks_link.py)"
    elif not stripped.startswith("{") and not stripped.endswith("=") and len(stripped) % 4 != 0:
        hint = " (base64 padding may be missing — regenerate the link)"
    raise AppError("INVALID_PAYLOAD", f"Invalid calculation link payload{hint}", 400) from last_error


def decode_payload(payload_b64: str) -> tuple[str, EworksLinkPayload]:
    if not payload_b64 or not payload_b64.strip():
        raise AppError("MISSING_PAYLOAD", "Missing calculation link payload", 400)
    raw = payload_b64.strip()
    try:
        data = _decode_payload_bytes(raw)
        if raw.startswith("{"):
            # Signatures are computed on the canonical base64 form.
            raw = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()
        return raw, EworksLinkPayload.model_validate(data)
    except json.JSONDecodeError as exc:
        raise AppError("INVALID_PAYLOAD", "Invalid calculation link payload: not valid JSON", 400) from exc
    except ValidationError as exc:
        missing = [err["loc"][0] for err in exc.errors() if err["type"] == "missing"]
        if missing:
            fields = ", ".join(str(field) for field in missing)
            raise AppError(
                "INVALID_PAYLOAD",
                f"Invalid calculation link payload: missing required fields ({fields})",
                400,
            ) from exc
        raise AppError("INVALID_PAYLOAD", "Invalid calculation link payload: field validation failed", 400) from exc
    except AppError:
        raise
    except (binascii.Error, ValueError) as exc:
        raise AppError("INVALID_PAYLOAD", "Invalid calculation link payload", 400) from exc


def verify_signature(payload_raw: str, sig: str | None) -> None:
    if not settings.eworks_link_sig_required:
        return
    if not sig:
        raise AppError("INVALID_SIGNATURE", "Missing link signature", 401)
    expected = hmac.new(_link_secret().encode(), payload_raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig.strip()):
        raise AppError("INVALID_SIGNATURE", "Invalid link signature", 401)


def assert_not_expired(expires_at: datetime) -> None:
    now = datetime.now(timezone.utc)
    expires = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if expires <= now:
        raise AppError("EXPIRED_LINK", "Calculation link has expired", 410)


def resolve_client(db: Session, client_name: str) -> Client:
    client = find_client_by_name_or_alias(db, client_name)
    if client is None:
        raise AppError("CLIENT_NOT_FOUND", f"Client not found: {client_name}", 404)
    return client


def resolve_client_for_link(db: Session, client_name: str) -> Client:
    """Ensure the client exists so the link can open; rules may be configured later."""
    client, _created, _alias = get_or_create_client_for_import(db, client_name)
    return client


def try_resolve_rate_rule(db: Session, client_id: UUID, trade_id: UUID) -> RateRule | None:
    matched = find_active_rule(db, client_id, trade_id, date.today())
    if matched is None or matched.rule.client_id != client_id:
        return None
    return matched.rule


def build_resolved_rule_info(
    client: Client,
    trade: Trade,
    rule: RateRule | None,
    *,
    link_client_name: str,
    eworks_client_fee_pct: Decimal | None = None,
) -> ResolvedRuleInfo:
    display_client = link_client_name.strip() or client.name
    if rule is not None:
        return ResolvedRuleInfo(
            client_id=client.id,
            trade_id=trade.id,
            rule_id=rule.id,
            rule_version=rule.version,
            formula_source=rule.formula_source,
            xlsx_client_name=rule.xlsx_client_name or display_client,
            xlsx_trade_name=rule.xlsx_trade_name or trade.name,
            client_fee_pct=rule.client_fee_pct,
        )
    fee_pct = eworks_client_fee_pct if eworks_client_fee_pct is not None else Decimal("0")
    return ResolvedRuleInfo(
        client_id=client.id,
        trade_id=trade.id,
        rule_id=None,
        rule_version="",
        formula_source="none",
        xlsx_client_name=display_client,
        xlsx_trade_name=trade.name,
        client_fee_pct=fee_pct,
    )


def session_eworks_client_fee_pct(session: CalculationSession) -> Decimal | None:
    return client_fee_pct_from_snapshot(session.eworks_customer_snapshot)


def _fetch_eworks_customer_snapshot(customer_name: str) -> dict | None:
    if not settings.eworks_api_enabled:
        return None
    snapshot = fetch_customer_by_name(customer_name)
    return snapshot.model_dump_for_session()


def client_has_trade_rate_rule(db: Session, client_id: UUID | None, trade_id: UUID | None) -> bool:
    if client_id is None or trade_id is None:
        return False
    matched = find_active_rule(db, client_id, trade_id, date.today())
    return matched is not None and matched.rule.client_id == client_id


def resolve_trade(db: Session, trade_name: str) -> Trade:
    normalized = normalize_trade_name(trade_name)
    trade = db.scalar(select(Trade).where(Trade.name == normalized))
    if trade is None:
        raise AppError("TRADE_NOT_FOUND", f"Trade not found: {trade_name}", 404)
    return trade


def resolve_rate_rule(db: Session, client_id: UUID, trade_id: UUID):
    matched = find_active_rule(db, client_id, trade_id, date.today())
    if matched is None:
        raise AppError("RULE_NOT_FOUND", "No active rate rule found for client and trade", 404)
    return matched.rule


def resolve_skill_trade(db: Session, skill_name: str | None, *, fallback_trade_name: str) -> Trade:
    name = (skill_name or "").strip() or fallback_trade_name.strip()
    return resolve_trade(db, name)


def work_skill_name(block: WorkBlockSnapshot, fallback_trade_name: str) -> str:
    return normalize_trade_name((block.skill_required or "").strip() or fallback_trade_name)


def collect_work_skills(works: list[WorkBlockSnapshot], fallback_trade_name: str) -> list[str]:
    if not works:
        raise AppError("WORKS_REQUIRED", "At least one work block is required", 400)
    return list(dict.fromkeys(work_skill_name(block, fallback_trade_name) for block in works))


def skills_are_uniform(works: list[WorkBlockSnapshot], fallback_trade_name: str) -> bool:
    return len(collect_work_skills(works, fallback_trade_name)) <= 1


def build_quote_description(payload: EworksLinkPayload) -> str | None:
    if payload.quote_description:
        return payload.quote_description
    parts: list[str] = []
    if payload.access_notes:
        parts.append(f"Access: {payload.access_notes}")
    if payload.original_job_description:
        parts.append(f"Quote: {payload.original_job_description}")
    if payload.booked_by:
        parts.append(f"Info: Booked by {payload.booked_by}")
    if payload.travel_notes:
        parts.append(f"Travel: {payload.travel_notes}")
    if payload.contact:
        parts.append(f"Contact: {payload.contact}")
    if payload.quote_screening_answers:
        parts.append(f"Quote Screening Answers:\n{payload.quote_screening_answers}")
    return "\n\n".join(parts) if parts else None


def payload_to_step1(
    payload: EworksLinkPayload,
    client: Client,
    trade: Trade,
    *,
    client_display_name: str | None = None,
) -> Step1Snapshot:
    return Step1Snapshot(
        quote_number=payload.quote_number,
        job_number=payload.job_number,
        external_job_id=payload.external_job_id or payload.source,
        engineer_name=payload.engineer_name,
        client_name=client_display_name or client.name,
        trade_name=trade.name,
        property_address=payload.property_address,
        property_manager_name=payload.property_manager,
        property_manager_email=payload.property_manager_email,
        property_manager_phone=payload.property_manager_phone,
        tenant_name=payload.tenant_name,
        tenant_phone=payload.tenant_phone,
        access_notes=payload.access_notes,
        original_job_description=payload.original_job_description,
        booked_by=payload.booked_by,
        contact=payload.contact,
        quote_screening_answers=payload.quote_screening_answers,
        date_visited=payload.date_visited,
        travel_time_minutes=payload.travel_time_minutes,
        travel_notes=payload.travel_notes,
        parking_notes=payload.parking_notes,
        total_time_for_job=payload.total_time_for_job,
        quote_description=build_quote_description(payload),
        findings_report=payload.findings_report,
        congestion_required=payload.congestion_required,
        congestion_amount=payload.congestion_amount,
        travel=payload.travel,
    )


def find_session_by_idempotency_key(db: Session, key: str) -> CalculationSession | None:
    now = datetime.now(timezone.utc)
    session = db.scalar(
        select(CalculationSession)
        .where(CalculationSession.idempotency_key == key)
        .where(CalculationSession.expires_at > now)
    )
    return session


def find_resumable_session(db: Session, payload: EworksLinkPayload) -> CalculationSession | None:
    key = session_idempotency_key(payload.source, payload.quote_number, payload.job_number)
    return find_session_by_idempotency_key(db, key)


def _session_ui_state(session: CalculationSession) -> SessionUiState | None:
    if not session.ui_state:
        return None
    return SessionUiState.model_validate(session.ui_state)


def _build_session_response(
    session: CalculationSession,
    *,
    step1: Step1Snapshot,
    step2: Step2Snapshot | None,
    resolved: ResolvedRuleInfo,
    resumed: bool,
) -> CalculationSessionFromLinkResponse:
    return CalculationSessionFromLinkResponse(
        session_id=session.id,
        session_token=session.session_token,
        step1=step1,
        step2=step2,
        resolved=resolved,
        expires_at=session.expires_at,
        ui_state=_session_ui_state(session),
        resumed=resumed,
    )


def create_session_from_link(db: Session, *, payload_b64: str, sig: str | None) -> CalculationSessionFromLinkResponse:
    payload_raw, payload = decode_payload(payload_b64)
    verify_signature(payload_raw, sig)
    assert_not_expired(payload.expires_at)

    eworks_snapshot_dict = _fetch_eworks_customer_snapshot(payload.client)
    eworks_fee_pct = client_fee_pct_from_snapshot(eworks_snapshot_dict)

    client = resolve_client_for_link(db, payload.client)
    trade = resolve_trade(db, payload.trade)
    rule = try_resolve_rate_rule(db, client.id, trade.id)
    link_client_name = payload.client.strip()
    step1 = payload_to_step1(payload, client, trade, client_display_name=link_client_name)
    resolved = build_resolved_rule_info(
        client,
        trade,
        rule,
        link_client_name=link_client_name,
        eworks_client_fee_pct=eworks_fee_pct if rule is None else None,
    )
    idempotency_key = session_idempotency_key(payload.source, payload.quote_number, payload.job_number)

    existing = find_session_by_idempotency_key(db, idempotency_key)
    if existing is not None:
        existing.step1_snapshot = step1.model_dump(mode="json")
        existing.payload_snapshot = payload.model_dump(mode="json")
        existing.client_id = client.id
        existing.trade_id = trade.id
        existing.rate_rule_id = rule.id if rule else None
        existing.eworks_customer_snapshot = eworks_snapshot_dict
        db.flush()
        step2 = Step2Snapshot.model_validate(existing.step2_snapshot) if existing.step2_snapshot else None
        resolved = build_resolved_rule_info(
            client,
            trade,
            rule,
            link_client_name=link_client_name,
            eworks_client_fee_pct=eworks_fee_pct if rule is None else None,
        )
        response = _build_session_response(existing, step1=step1, step2=step2, resolved=resolved, resumed=True)
        store_idempotency(
            db,
            key=idempotency_key,
            request_hash=hash_payload(payload_raw),
            response_payload=response.model_dump(mode="json"),
            expires_at=existing.expires_at,
        )
        return response

    initial_step2 = step2_from_link_questionnaire(payload, trade.name)

    session = CalculationSession(
        session_token=secrets.token_hex(32),
        idempotency_key=idempotency_key,
        source=payload.source,
        payload_snapshot=payload.model_dump(mode="json"),
        step1_snapshot=step1.model_dump(mode="json"),
        step2_snapshot=initial_step2.model_dump(mode="json") if initial_step2 else None,
        ui_state=SessionUiState().model_dump(mode="json"),
        client_id=client.id,
        trade_id=trade.id,
        rate_rule_id=rule.id if rule else None,
        eworks_customer_snapshot=eworks_snapshot_dict,
        expires_at=payload.expires_at if payload.expires_at.tzinfo else payload.expires_at.replace(tzinfo=timezone.utc),
    )
    db.add(session)
    db.flush()

    response = _build_session_response(
        session,
        step1=step1,
        step2=initial_step2,
        resolved=resolved,
        resumed=False,
    )
    store_idempotency(
        db,
        key=idempotency_key,
        request_hash=hash_payload(payload_raw),
        response_payload=response.model_dump(mode="json"),
        expires_at=session.expires_at,
    )
    return response


def build_signed_test_link(
    *,
    quote_number: str = "Q21863",
    job_number: str = "33629",
    client: str = "Lambert Chartered Surveyors",
    trade: str = "Carpenter",
    property_address: str = "The Factory, 1 Nile Street",
    engineer_name: str = "Alex Alves",
    days_valid: int = 30,
    frontend_url: str = "http://localhost:3000",
) -> tuple[str, str, dict, str]:
    """Build a signed eWorks link for local testing."""
    from urllib.parse import urlencode

    expires_at = (datetime.now(timezone.utc) + timedelta(days=days_valid)).replace(microsecond=0)
    payload = {
        "source": "eworks",
        "quote_number": quote_number,
        "job_number": job_number,
        "external_job_id": job_number,
        "engineer_name": engineer_name,
        "client": client,
        "trade": trade,
        "property_address": property_address,
        "property_manager": "Kira Mcintyre (Property Manager)",
        "access_notes": "To meet caretaker on site on 22nd May at 8am. Alex - 07960696064",
        "original_job_description": (
            "Please can you provide a quote\n"
            "To upgrade all doors marked for upgrade\n"
            "To replace all doors marked for upgrade\n"
            "I have attached the spreadsheet."
        ),
        "booked_by": "Billie",
        "travel_notes": "1st appt",
        "contact": "Alex - 07960696064",
        "quote_screening_answers": (
            "1. Unfortunately we do not have any pictures.\n"
            "2. We would like it back ASAP\n"
            "3. It would hopefully be within the week after reviewing and sharing it with the client\n"
            "4. We have reached out and are waiting for replies."
        ),
        "date_visited": "2026-05-22",
        "parking_notes": "",
        "total_time_for_job": "",
        "findings_report": "",
        "travel_time_minutes": 0,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "congestion_required": True,
        "congestion_amount": 18,
        "travel": 0,
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(_link_secret().encode(), raw.encode(), hashlib.sha256).hexdigest()
    query = urlencode({"payload": raw, "sig": sig})
    url = f"{frontend_url.rstrip('/')}/eworks/calculate?{query}"
    return raw, sig, payload, url


def create_dev_test_session(db: Session) -> CalculationSessionFromLinkResponse:
    if settings.environment != "development":
        raise AppError("NOT_FOUND", "Not found", 404)
    raw, sig, _, _ = build_signed_test_link()
    return create_session_from_link(db, payload_b64=raw, sig=sig)


def get_session_by_token(db: Session, session_id: UUID, session_token: str) -> CalculationSession:
    session = db.scalar(
        select(CalculationSession).where(
            CalculationSession.id == session_id,
            CalculationSession.session_token == session_token,
        )
    )
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Calculation session not found", 404)
    assert_not_expired(session.expires_at)
    return session
