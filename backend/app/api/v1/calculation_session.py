from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import DbSession
from app.core.exceptions import AppError, success_response
from app.models.rate_rule import RateRule
from app.schemas.eworks_link import (
    CalculateSessionRequest,
    CalculateSessionResponse,
    CalculationSessionFromLinkResponse,
    CalculationSessionRead,
    FromLinkRequest,
    ResolvedRuleInfo,
    SessionPdfRequest,
    SessionUiState,
    Step1Snapshot,
    Step2Snapshot,
    UpdateCalculationSessionRequest,
)
from app.services.calculation_session_pdf_service import render_session_quote_pdf
from app.services.calculation_session_service import add_session_attachment, calculate_session, update_session_step2
from app.services.eworks_link_service import create_dev_test_session, create_session_from_link, get_session_by_token

router = APIRouter(prefix="/calculation-session", tags=["calculation-session"])


def _session_read(db: Session, session) -> CalculationSessionRead:
    rule = db.get(RateRule, session.rate_rule_id)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    ui_state = SessionUiState.model_validate(session.ui_state) if session.ui_state else None
    return CalculationSessionRead(
        session_id=session.id,
        step1=Step1Snapshot.model_validate(session.step1_snapshot),
        step2=step2,
        resolved=ResolvedRuleInfo(
            client_id=session.client_id,
            trade_id=session.trade_id,
            rule_id=session.rate_rule_id,
            rule_version=rule.version if rule else "",
            formula_source=rule.formula_source if rule else "",
            xlsx_client_name=rule.xlsx_client_name if rule else None,
            xlsx_trade_name=rule.xlsx_trade_name if rule else None,
        ),
        expires_at=session.expires_at,
        ui_state=ui_state,
    )


def _require_session_token(
    session_id: UUID,
    db: DbSession,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
):
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    try:
        return get_session_by_token(db, session_id, x_session_token)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/from-link")
def from_link(payload: FromLinkRequest, db: DbSession):
    try:
        result = create_session_from_link(db, payload_b64=payload.payload, sig=payload.sig)
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(CalculationSessionFromLinkResponse.model_validate(result))


@router.post("/dev-bootstrap")
def dev_bootstrap(db: DbSession):
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")
    try:
        result = create_dev_test_session(db)
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(CalculationSessionFromLinkResponse.model_validate(result))


@router.get("/{session_id}")
def get_session(session_id: UUID, db: DbSession, session=Depends(_require_session_token)):
    return success_response(_session_read(db, session))


@router.patch("/{session_id}")
def patch_session(
    session_id: UUID,
    payload: UpdateCalculationSessionRequest,
    db: DbSession,
    session=Depends(_require_session_token),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    try:
        result = update_session_step2(
            db,
            session_id=session_id,
            session_token=session.session_token,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(result)


@router.post("/{session_id}/attachments")
async def upload_attachment(
    session_id: UUID,
    db: DbSession,
    session=Depends(_require_session_token),
    file: UploadFile = File(...),
    work_index: int = Query(default=0, ge=0),
):
    try:
        result = await add_session_attachment(
            db,
            session_id=session_id,
            session_token=session.session_token,
            upload=file,
            work_index=work_index,
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success_response(result)


@router.post("/{session_id}/calculate")
def run_calculate(
    session_id: UUID,
    db: DbSession,
    session=Depends(_require_session_token),
    body: CalculateSessionRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    try:
        result = calculate_session(
            db,
            session_id=session_id,
            session_token=session.session_token,
            step2=body.step2 if body else None,
            idempotency_key=idempotency_key,
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(CalculateSessionResponse.model_validate(result))


@router.post("/{session_id}/pdf")
def download_session_pdf(
    session_id: UUID,
    db: DbSession,
    session=Depends(_require_session_token),
    body: SessionPdfRequest | None = None,
):
    try:
        content, file_name, media_type = render_session_quote_pdf(
            db,
            session_id=session_id,
            session_token=session.session_token,
            is_draft=body.is_draft if body else False,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
