"""Engineer assigned jobs sourced from eWorks job sync (read-only)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.models.eworks_sync import EworksJob, EworksQuote
from app.services.quote_assignment_service import _as_uuid

# TODO: Expand payload field mapping once eWorks job assignee schema is confirmed.
_PAYLOAD_ASSIGNEE_FIELDS = (
    "engineer",
    "assigned_to",
    "staff",
    "operative",
    "user",
    "engineer_id",
    "assigned_user",
)

_DICT_EMAIL_KEYS = ("email", "user_email", "assigned_user_email")
_DICT_NAME_KEYS = ("name", "full_name", "user_name", "assigned_user_name")
_DICT_ID_KEYS = ("id", "user_id", "assigned_user_id", "engineer_id", "staff_id")


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _uuid_matches(value: object, user_id: UUID) -> bool:
    try:
        return UUID(str(value)) == user_id
    except (TypeError, ValueError):
        return str(value).strip().lower() == str(user_id).lower()


def _value_matches_user(value: object, *, user: AuthenticatedUser, user_id: UUID) -> bool:
    if value is None:
        return False

    if isinstance(value, dict):
        for key in _DICT_EMAIL_KEYS:
            if key in value and value[key]:
                if _normalize_text(str(value[key])) == _normalize_text(user.email):
                    return True
        for key in _DICT_NAME_KEYS:
            if key in value and value[key]:
                if _normalize_text(str(value[key])) == _normalize_text(user.name):
                    return True
        for key in _DICT_ID_KEYS:
            if key in value and value[key] is not None and _uuid_matches(value[key], user_id):
                return True
        return False

    if isinstance(value, (int, float)):
        return _uuid_matches(value, user_id)

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return False
        if "@" in normalized:
            return _normalize_text(normalized) == _normalize_text(user.email)
        if _uuid_matches(normalized, user_id):
            return True
        return _normalize_text(normalized) == _normalize_text(user.name)

    return False


def _payload_has_assignee_mapping(raw_payload: dict | None) -> bool:
    if not isinstance(raw_payload, dict):
        return False
    return any(field in raw_payload and raw_payload[field] is not None for field in _PAYLOAD_ASSIGNEE_FIELDS)


def _engineer_owns_eworks_job(job: EworksJob, *, user: AuthenticatedUser, user_id: UUID) -> bool:
    raw_payload = job.raw_payload if isinstance(job.raw_payload, dict) else None
    if not _payload_has_assignee_mapping(raw_payload):
        return False
    for field in _PAYLOAD_ASSIGNEE_FIELDS:
        if raw_payload is None or field not in raw_payload:
            continue
        if _value_matches_user(raw_payload[field], user=user, user_id=user_id):
            return True
    return False


def _quote_ref_for_job(db: Session, job: EworksJob) -> str | None:
    if job.eworks_quote_id is None:
        return None
    quote = (
        db.query(EworksQuote)
        .filter(EworksQuote.eworks_quote_id == job.eworks_quote_id)
        .order_by(EworksQuote.id.desc())
        .first()
    )
    if quote is None:
        return None
    return (quote.quote_ref or "").strip() or None


def build_engineer_assigned_job_read(db: Session, job: EworksJob) -> dict:
    total = None
    if job.total is not None:
        total = str(job.total)
    return {
        "id": job.id,
        "eworks_job_id": job.eworks_job_id,
        "job_ref": job.job_ref,
        "eworks_quote_id": job.eworks_quote_id,
        "quote_ref": _quote_ref_for_job(db, job),
        "customer_name": job.customer_name,
        "address": job.address,
        "status": job.status,
        "status_name": job.status_name,
        "job_date": job.job_date,
        "description": job.description,
        "total": total,
    }


def list_assigned_jobs_for_engineer(db: Session, user: AuthenticatedUser) -> list[dict]:
    user_id = _as_uuid(user.id)
    if user_id is None:
        return []

    rows = db.query(EworksJob).order_by(EworksJob.synced_at.desc()).all()
    results: list[dict] = []
    for row in rows:
        if not _engineer_owns_eworks_job(row, user=user, user_id=user_id):
            continue
        results.append(build_engineer_assigned_job_read(db, row))
    return results
