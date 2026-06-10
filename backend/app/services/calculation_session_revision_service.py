from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.models.calculation_session_version import CalculationSessionVersion
from app.models.quote_assignment import EworksQuoteAssignment
from app.schemas.calculation_session_revision import (
    CalculationSessionVersionRead,
    ReviseEstimateRequest,
    ReviseEstimateResponse,
    SessionVersionHistoryResponse,
)
from app.services.eworks_link_service import get_session_by_token

_SENSITIVE_BREAKDOWN_KEYS = frozenset(
    {
        "profit_gbp",
        "profit_pct",
        "direct_labour_cost",
        "formula_version",
        "formula_source",
        "xlsx_formula_version",
        "internal_notes",
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _calculation_result_from_session(session: CalculationSession) -> dict | None:
    if not isinstance(session.ui_state, dict):
        return None
    last_result = session.ui_state.get("last_result")
    return last_result if isinstance(last_result, dict) else None


def _final_total_from_result(calculation_result: dict | None) -> Decimal | None:
    if not calculation_result:
        return None
    breakdown = calculation_result.get("breakdown")
    if not isinstance(breakdown, dict):
        return None
    raw_total = breakdown.get("final_total")
    if raw_total is None:
        return None
    return Decimal(str(raw_total))


def _sanitize_breakdown(breakdown: dict | None) -> dict | None:
    if not isinstance(breakdown, dict):
        return None
    sanitized = {key: value for key, value in breakdown.items() if key not in _SENSITIVE_BREAKDOWN_KEYS}
    labour = sanitized.get("labour")
    if isinstance(labour, list):
        sanitized["labour"] = [
            {k: v for k, v in line.items() if k != "formula"} if isinstance(line, dict) else line for line in labour
        ]
    return sanitized


def _sanitize_calculation_result(calculation_result: dict | None) -> dict | None:
    if not isinstance(calculation_result, dict):
        return None
    payload = dict(calculation_result)
    breakdown = payload.get("breakdown")
    if isinstance(breakdown, dict):
        payload["breakdown"] = _sanitize_breakdown(breakdown)
    work_breakdowns = payload.get("work_breakdowns")
    if isinstance(work_breakdowns, list):
        payload["work_breakdowns"] = [
            {
                **item,
                "breakdown": _sanitize_breakdown(item.get("breakdown") if isinstance(item, dict) else None),
                "internal_notes": None,
            }
            if isinstance(item, dict)
            else item
            for item in work_breakdowns
        ]
    payload.pop("internal_notes", None)
    payload.pop("internal_view", None)
    return payload


def _assignment_for_session(db: Session, session_id: UUID) -> EworksQuoteAssignment | None:
    return db.scalar(
        select(EworksQuoteAssignment)
        .where(EworksQuoteAssignment.calculation_session_id == session_id)
        .order_by(EworksQuoteAssignment.id.desc())
        .limit(1)
    )


def resolve_session_submitter(
    db: Session,
    session: CalculationSession,
) -> tuple[UUID | None, str | None, str | None]:
    if session.submitted_by_user_id is not None:
        return session.submitted_by_user_id, session.submitted_by_name, session.submitted_by_email

    name = (session.submitted_by_name or "").strip()
    if name and name.lower() not in {"unknown", "unknown submitter"}:
        return session.submitted_by_user_id, session.submitted_by_name, session.submitted_by_email

    assignment = _assignment_for_session(db, session.id)
    if assignment is not None:
        return assignment.assigned_user_id, assignment.assigned_user_name, assignment.assigned_user_email

    from app.services.quote_assignment_service import resolve_session_submitter_identity

    identity = resolve_session_submitter_identity(db, session)
    resolved_name = identity.get("submitted_by_name")
    if resolved_name and resolved_name != "Unknown submitter":
        return (
            identity.get("submitted_by_user_id"),
            resolved_name,
            identity.get("submitted_by_email"),
        )
    return None, None, None


def apply_submitter_to_session(db: Session, session: CalculationSession) -> None:
    user_id, name, email = resolve_session_submitter(db, session)
    if user_id is not None:
        session.submitted_by_user_id = user_id
    if name:
        session.submitted_by_name = name.strip()
    if email:
        session.submitted_by_email = email.strip()


def assert_revision_owner(
    db: Session,
    *,
    session: CalculationSession,
    owner_user_id: UUID | None = None,
) -> None:
    submitter_id, _, _ = resolve_session_submitter(db, session)
    if submitter_id is None:
        return
    if owner_user_id is None:
        return
    if submitter_id != owner_user_id:
        raise AppError("REVISION_FORBIDDEN", "Only the estimate owner can revise this submission", 403)


def _mark_versions_not_current(db: Session, session_id: UUID) -> None:
    db.execute(
        update(CalculationSessionVersion)
        .where(CalculationSessionVersion.session_id == session_id, CalculationSessionVersion.is_current.is_(True))
        .values(is_current=False)
    )


def create_session_version_snapshot(
    db: Session,
    *,
    session: CalculationSession,
    version_number: int,
    revision_reason: str | None,
    is_current: bool,
) -> CalculationSessionVersion:
    submitter_id = session.submitted_by_user_id
    submitter_name = session.submitted_by_name
    submitter_email = session.submitted_by_email
    if submitter_id is None:
        submitter_id, submitter_name, submitter_email = resolve_session_submitter(db, session)

    if is_current:
        _mark_versions_not_current(db, session.id)

    row = CalculationSessionVersion(
        session_id=session.id,
        version_number=version_number,
        step1_snapshot=dict(session.step1_snapshot or {}),
        step2_snapshot=dict(session.step2_snapshot) if session.step2_snapshot else None,
        calculation_result=_calculation_result_from_session(session),
        submitted_at=session.submitted_at or _now(),
        submitted_by_user_id=submitter_id,
        submitted_by_name=submitter_name,
        submitted_by_email=submitter_email,
        revision_reason=revision_reason,
        status="submitted",
        is_current=is_current,
    )
    db.add(row)
    db.flush()
    return row


def ensure_current_version_snapshotted(db: Session, session: CalculationSession) -> CalculationSessionVersion | None:
    if session.current_version_number <= 0:
        return None
    existing = db.scalar(
        select(CalculationSessionVersion).where(
            CalculationSessionVersion.session_id == session.id,
            CalculationSessionVersion.version_number == session.current_version_number,
        )
    )
    if existing is not None:
        return existing
    return create_session_version_snapshot(
        db,
        session=session,
        version_number=session.current_version_number,
        revision_reason=None,
        is_current=True,
    )


def start_estimate_revision(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    payload: ReviseEstimateRequest,
    owner_user_id: UUID | None = None,
) -> ReviseEstimateResponse:
    reason = (payload.reason or "").strip()
    if not reason:
        raise AppError("REVISION_REASON_REQUIRED", "A revision reason is required", 400)

    session = get_session_by_token(db, session_id, session_token)
    if session.status != "submitted" or not session.locked:
        raise AppError("SESSION_NOT_REVISABLE", "Only locked submitted estimates can be revised", 409)
    if session.revision_in_progress:
        raise AppError("REVISION_IN_PROGRESS", "A revision is already in progress", 409)

    assert_revision_owner(db, session=session, owner_user_id=owner_user_id)

    if session.current_version_number <= 0:
        session.current_version_number = 1
    ensure_current_version_snapshotted(db, session)

    session.status = "revision_in_progress"
    session.revision_in_progress = True
    session.active_revision_reason = reason
    session.locked = False
    session.last_revised_at = _now()
    db.flush()

    return ReviseEstimateResponse(
        session_id=session.id,
        resume_url=f"/eworks/calculate?session_id={session.id}",
        revision_in_progress=True,
        active_revision_reason=reason,
        current_version_number=session.current_version_number,
    )


def complete_revision_submit(db: Session, session: CalculationSession) -> None:
    if not session.revision_in_progress:
        if session.current_version_number <= 0:
            apply_submitter_to_session(db, session)
            create_session_version_snapshot(
                db,
                session=session,
                version_number=1,
                revision_reason=None,
                is_current=True,
            )
            session.current_version_number = 1
        else:
            ensure_current_version_snapshotted(db, session)
        session.locked = True
        return

    next_version = max(session.current_version_number, 1) + 1
    create_session_version_snapshot(
        db,
        session=session,
        version_number=next_version,
        revision_reason=session.active_revision_reason,
        is_current=True,
    )
    session.current_version_number = next_version
    session.revision_in_progress = False
    session.active_revision_reason = None
    session.locked = True
    apply_submitter_to_session(db, session)


def session_is_editable(session: CalculationSession) -> bool:
    if session.revision_in_progress and not session.locked:
        return True
    if session.status in {"in_progress", "revision_in_progress"} and not session.locked:
        return True
    return session.status not in {"submitted"} and not session.locked


def assert_session_editable(session: CalculationSession) -> None:
    if session.locked and not session.revision_in_progress:
        raise AppError("SESSION_LOCKED", "This estimate is locked after submission", 409)
    if session.status == "submitted" and not session.revision_in_progress:
        raise AppError("SESSION_SUBMITTED", "Cannot update questionnaire after submission", 409)


def version_to_read(row: CalculationSessionVersion) -> CalculationSessionVersionRead:
    calculation_result = _sanitize_calculation_result(row.calculation_result)
    return CalculationSessionVersionRead(
        version_number=row.version_number,
        submitted_at=row.submitted_at,
        submitted_by_name=row.submitted_by_name,
        submitted_by_email=row.submitted_by_email,
        revision_reason=row.revision_reason,
        final_total=_final_total_from_result(row.calculation_result),
        status=row.status,
        is_current=row.is_current,
    )


def list_session_version_history(db: Session, session_id: UUID) -> SessionVersionHistoryResponse:
    session = db.get(CalculationSession, session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)

    rows = db.scalars(
        select(CalculationSessionVersion)
        .where(CalculationSessionVersion.session_id == session_id)
        .order_by(CalculationSessionVersion.version_number.desc())
    ).all()
    versions = [version_to_read(row) for row in rows]
    return SessionVersionHistoryResponse(
        session_id=session_id,
        current_version_number=session.current_version_number,
        revision_in_progress=session.revision_in_progress,
        active_revision_reason=session.active_revision_reason,
        versions=versions,
    )


def get_session_version(
    db: Session,
    *,
    session_id: UUID,
    version_number: int,
) -> CalculationSessionVersion:
    row = db.scalar(
        select(CalculationSessionVersion).where(
            CalculationSessionVersion.session_id == session_id,
            CalculationSessionVersion.version_number == version_number,
        )
    )
    if row is None:
        raise AppError("VERSION_NOT_FOUND", "Estimate version not found", 404)
    return row


def apply_version_snapshot_to_session(db: Session, version: CalculationSessionVersion) -> CalculationSession:
    session = db.get(CalculationSession, version.session_id)
    if session is None:
        raise AppError("SESSION_NOT_FOUND", "Quote session not found", 404)
    session.step1_snapshot = dict(version.step1_snapshot or {})
    session.step2_snapshot = dict(version.step2_snapshot) if version.step2_snapshot else None
    if version.calculation_result:
        session.ui_state = {
            "current_step": 3,
            "max_reachable_step": 3,
            "last_result": version.calculation_result,
        }
    return session
