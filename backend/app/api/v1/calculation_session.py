from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser, require_roles, try_get_optional_current_user
from app.core.config import settings
from app.core.security import UserRole
from app.db.session import DbSession
from app.core.exceptions import AppError, success_response
from app.schemas.calculation_session_revision import ReviseEstimateRequest, ReviseEstimateResponse
from app.schemas.eworks_link import (
    CalculateSessionRequest,
    CalculateSessionResponse,
    CalculationSessionFromLinkResponse,
    CalculationSessionRead,
    FromLinkRequest,
    ManualCalculationSessionRequest,
    ResolvedRuleInfo,
    RewordScopeRequest,
    RewordScopeResponse,
    SessionPdfRequest,
    SessionUiState,
    Step1Snapshot,
    Step2Snapshot,
    SubmitSessionResponse,
    UpdateCalculationSessionRequest,
)
from app.services.audit_helpers import record_audit
from app.services.manual_calculation_session_service import create_manual_calculation_session
from app.services.calculation_session_pdf_service import render_session_quote_pdf
from app.services.calculation_session_revision_service import start_estimate_revision
from app.services.calculation_session_service import (
    add_session_attachment,
    calculate_session,
    delete_session_attachment,
    get_session_attachment_meta,
    submit_session,
    update_session_step2,
)
from app.services.scope_reword_service import reword_scope_text
from app.services.eworks_attachment_service import read_session_attachment
from app.services.eworks_link_service import create_dev_test_session, create_session_from_link, get_session_by_token

router = APIRouter(prefix="/calculation-session", tags=["calculation-session"])

StaffEstimateCreator = Annotated[
    AuthenticatedUser,
    Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR)),
]

OptionalStaffUser = Annotated[AuthenticatedUser | None, Depends(try_get_optional_current_user)]


def _session_read(db: Session, session) -> CalculationSessionRead:
    from app.services.calculation_session_service import _resolved_from_session

    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    ui_state = SessionUiState.model_validate(session.ui_state) if session.ui_state else None
    return CalculationSessionRead(
        session_id=session.id,
        step1=Step1Snapshot.model_validate(session.step1_snapshot),
        step2=step2,
        resolved=_resolved_from_session(db, session),
        expires_at=session.expires_at,
        ui_state=ui_state,
        status=session.status,
        locked=session.locked,
        revision_in_progress=session.revision_in_progress,
        active_revision_reason=session.active_revision_reason,
        current_version_number=session.current_version_number,
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
    result = create_session_from_link(db, payload_b64=payload.payload, sig=payload.sig)
    db.commit()
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


@router.post("/manual")
def create_manual_session(
    body: ManualCalculationSessionRequest,
    db: DbSession,
    actor: StaffEstimateCreator,
):
    try:
        result = create_manual_calculation_session(
            db,
            quote_ref=body.quote_ref,
            job_ref=body.job_ref,
            client_name=body.client_name,
            trade_name=body.trade_name,
        )
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    record_audit(
        db,
        actor=actor,
        action="manual_estimate_created",
        entity_type="calculation_session",
        entity_id=result.session_id,
        before=None,
        after={
            "session_id": str(result.session_id),
            "source": "manual",
            "quote_ref": body.quote_ref,
            "job_ref": body.job_ref,
            "client_name": body.client_name or "Manual Estimate",
            "trade_name": body.trade_name,
        },
    )
    db.commit()
    return success_response(result)


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


@router.get("/{session_id}/attachments/{attachment_id}")
async def get_attachment(
    session_id: UUID,
    attachment_id: str,
    db: DbSession,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    token: str | None = Query(default=None),
):
    session_token = x_session_token or token
    if not session_token:
        raise HTTPException(status_code=401, detail="Missing session token")
    try:
        get_session_by_token(db, session_id, session_token)
        meta = get_session_attachment_meta(db, session_id, attachment_id)
        data, _ = await read_session_attachment(session_id, meta.stored_name)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Attachment file not found") from exc
    return Response(
        content=data,
        media_type=meta.content_type,
        headers={"Content-Disposition": f'inline; filename="{meta.file_name}"'},
    )


@router.delete("/{session_id}/attachments/{attachment_id}", status_code=204)
async def remove_attachment(
    session_id: UUID,
    attachment_id: str,
    db: DbSession,
    session=Depends(_require_session_token),
):
    try:
        await delete_session_attachment(
            db,
            session_id=session_id,
            session_token=session.session_token,
            attachment_id=attachment_id,
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(status_code=204)


@router.post("/{session_id}/reword-scope")
def reword_scope(
    session_id: UUID,
    payload: RewordScopeRequest,
    db: DbSession,
    session=Depends(_require_session_token),
):
    _ = session  # session token validated; no session mutation required
    try:
        reworded_text = reword_scope_text(payload.text)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(RewordScopeResponse(reworded_text=reworded_text))


@router.post("/{session_id}/revise")
def revise_estimate(
    session_id: UUID,
    payload: ReviseEstimateRequest,
    db: DbSession,
    session=Depends(_require_session_token),
    actor: OptionalStaffUser = None,
):
    if actor is not None and actor.role not in {UserRole.ADMIN, UserRole.ESTIMATOR, UserRole.ENGINEER}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    try:
        owner_user_id = UUID(str(actor.id)) if actor is not None else None
        result = start_estimate_revision(
            db,
            session_id=session_id,
            session_token=session.session_token,
            payload=payload,
            owner_user_id=owner_user_id,
        )
        record_audit(
            db,
            actor=actor,
            action="estimate_revision_started",
            entity_type="calculation_session",
            entity_id=session_id,
            after={
                "revision_in_progress": True,
                "active_revision_reason": payload.reason.strip(),
                "current_version_number": result.current_version_number,
            },
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(ReviseEstimateResponse.model_validate(result))


@router.post("/{session_id}/submit")
def submit_quote(
    session_id: UUID,
    db: DbSession,
    session=Depends(_require_session_token),
    body: CalculateSessionRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    was_revision = session.revision_in_progress
    previous_version = session.current_version_number
    try:
        submit_session(
            db,
            session_id=session_id,
            session_token=session.session_token,
            step2=body.step2 if body else None,
            idempotency_key=idempotency_key,
        )
        session = get_session_by_token(db, session_id, session.session_token)
        record_audit(
            db,
            actor=None,
            action="estimate_revision_submitted" if was_revision else "estimate_submitted",
            entity_type="calculation_session",
            entity_id=session_id,
            after={
                "version_number": session.current_version_number,
                "revision": was_revision,
            },
        )
        db.commit()
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(
        SubmitSessionResponse(
            submitted=True,
            version_number=session.current_version_number,
            revision=was_revision and session.current_version_number > max(previous_version, 0),
        )
    )


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
