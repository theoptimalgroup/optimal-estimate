"""Create blank manual calculation sessions for authenticated staff."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.models.trade import Trade
from app.schemas.eworks_link import ManualCalculationSessionResponse, SessionUiState, Step1Snapshot, Step2Snapshot
from app.services.client_service import get_or_create_client_for_import
from app.services.eworks_link_service import resolve_trade, try_resolve_rate_rule
from app.services.eworks_questionnaire_service import apply_questionnaire_defaults

DEFAULT_TOKEN_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _default_trade(db: Session) -> Trade:
    trade = db.scalar(select(Trade).where(Trade.is_active.is_(True)).order_by(Trade.name).limit(1))
    if trade is None:
        trade = db.scalar(select(Trade).order_by(Trade.name).limit(1))
    if trade is None:
        raise AppError("TRADE_NOT_CONFIGURED", "No trade configured for estimate session", 400)
    return trade


def _resolve_trade_for_manual(db: Session, trade_name: str | None) -> Trade:
    if trade_name and trade_name.strip():
        return resolve_trade(db, trade_name.strip())
    return _default_trade(db)


def _generate_quote_number(quote_ref: str | None) -> str:
    if quote_ref and quote_ref.strip():
        return quote_ref.strip()
    return f"MAN-{uuid4().hex[:8].upper()}"


def build_manual_resume_url(session_id: UUID, session_token: str) -> str:
    params = urlencode({"session_id": str(session_id), "token": session_token})
    return f"/eworks/calculate?{params}"


def create_manual_calculation_session(
    db: Session,
    *,
    quote_ref: str | None = None,
    job_ref: str | None = None,
    client_name: str | None = None,
    trade_name: str | None = None,
) -> ManualCalculationSessionResponse:
    display_client = (client_name or "").strip() or "Manual Estimate"
    client, _, _ = get_or_create_client_for_import(db, display_client)
    trade = _resolve_trade_for_manual(db, trade_name)
    rule = try_resolve_rate_rule(db, client.id, trade.id)

    quote_number = _generate_quote_number(quote_ref)
    job_number = (job_ref or "").strip()

    step1 = Step1Snapshot(
        quote_number=quote_number,
        job_number=job_number,
        external_job_id=None,
        client_name=display_client,
        trade_name=trade.name,
        property_address="",
    )

    payload_snapshot = {
        "source": "manual",
        "quote_number": quote_number,
        "job_number": job_number,
        "client": display_client,
        "trade": trade.name,
        "property_address": "",
    }

    initial_step2 = apply_questionnaire_defaults(Step2Snapshot(), trade_name=trade.name, default_skill=True)

    session = CalculationSession(
        session_token=secrets.token_hex(32),
        idempotency_key=f"manual.{uuid4()}",
        source="manual",
        payload_snapshot=payload_snapshot,
        step1_snapshot=step1.model_dump(mode="json"),
        step2_snapshot=initial_step2.model_dump(mode="json"),
        ui_state=SessionUiState().model_dump(mode="json"),
        client_id=client.id,
        trade_id=trade.id,
        rate_rule_id=rule.id if rule else None,
        eworks_customer_snapshot=None,
        expires_at=_now() + timedelta(days=DEFAULT_TOKEN_DAYS),
    )
    db.add(session)
    db.flush()

    return ManualCalculationSessionResponse(
        session_id=session.id,
        session_token=session.session_token,
        resume_url=build_manual_resume_url(session.id, session.session_token),
    )
