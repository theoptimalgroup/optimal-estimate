"""Extract, store, and resolve eWorks job appointments from synced payloads."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.models.eworks_sync import EworksJob, EworksJobAppointment

logger = logging.getLogger(__name__)

_APPOINTMENT_LIST_KEYS = (
    "appointments",
    "Appointments",
    "job_appointments",
    "Job_Appointments",
    "diary",
    "visits",
    "completed_appointments",
)

_USER_OBJECT_KEYS = ("user", "User", "staff", "operative", "assigned_to", "engineer", "employee")
_APPOINTMENT_TYPE_KEYS = (
    "appointment_type",
    "appointment_type_name",
    "Appointment_Type",
    "type",
    "Type",
)
_STATUS_KEYS = ("status", "Status", "appointment_status", "Appointment_Status")
_START_KEYS = (
    "start_at",
    "start_date",
    "Start_Date",
    "date_from",
    "appointment_start",
    "start_datetime",
    "start",
)
_END_KEYS = (
    "end_at",
    "end_date",
    "End_Date",
    "date_to",
    "appointment_end",
    "end_datetime",
    "end",
)
_START_TIME_KEYS = ("start_time", "Start_Time", "time_from")
_END_TIME_KEYS = ("end_time", "End_Time", "time_to")

_CANCELLED_STATUS_MARKERS = (
    "cancelled",
    "canceled",
    "cancelled by customer",
    "rejected",
)

_DICT_EMAIL_KEYS = ("email", "user_email", "Email")
_DICT_NAME_KEYS = ("name", "full_name", "user_name", "display_name", "Full_Name")
_DICT_ID_KEYS = ("id", "user_id", "staff_id", "engineer_id")


class SafeJobAppointment(TypedDict):
    appointment_id: int | None
    user_name: str | None
    user_email: str | None
    user_id: int | None
    appointment_type: str | None
    status: str | None
    start_at: str | None
    end_at: str | None


def _as_str(value: object | None, *, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if max_len is not None:
        return text[:max_len]
    return text


def _as_int(value: object | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pick(raw: dict[str, Any], *keys: str) -> object | None:
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def _pick_user_object(raw: dict[str, Any]) -> dict[str, Any] | str | None:
    for key in _USER_OBJECT_KEYS:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return None


def _extract_user_fields(user_value: object | None) -> tuple[int | None, str | None, str | None]:
    if user_value is None:
        return None, None, None

    if isinstance(user_value, dict):
        user_id = _as_int(_pick(user_value, *_DICT_ID_KEYS))
        user_email = _as_str(_pick(user_value, *_DICT_EMAIL_KEYS), max_len=320)
        user_name = _as_str(_pick(user_value, *_DICT_NAME_KEYS), max_len=500)
        if not user_name:
            user_name = _as_str(user_value.get("label"), max_len=500)
        return user_id, user_name, user_email

    text = _as_str(user_value, max_len=500)
    if not text:
        return None, None, None
    if "@" in text:
        return None, None, text[:320]
    return None, text, None


def _combine_date_time(date_value: object | None, time_value: object | None) -> str | None:
    date_text = _as_str(date_value, max_len=30)
    time_text = _as_str(time_value, max_len=20)
    if date_text and time_text:
        return f"{date_text} {time_text}"[:50]
    return date_text or time_text


def _extract_datetime(raw: dict[str, Any], start: bool) -> str | None:
    keys = _START_KEYS if start else _END_KEYS
    time_keys = _START_TIME_KEYS if start else _END_TIME_KEYS
    direct = _as_str(_pick(raw, *keys), max_len=50)
    if direct and any(sep in direct for sep in (" ", "T", " to ", "-")):
        return direct
    date_value = _pick(raw, *keys)
    time_value = _pick(raw, *time_keys)
    combined = _combine_date_time(date_value, time_value)
    if combined:
        return combined
    return direct


def _appointment_list_from_raw(raw_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(raw_payload, dict):
        return []
    for key in _APPOINTMENT_LIST_KEYS:
        value = raw_payload.get(key)
        if key == "completed_appointments":
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = value.get("items") or value.get("data") or value.get("appointments")
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
            continue
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def appointment_source_payload(job: EworksJob, raw_payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if isinstance(job.raw_detail_payload, dict):
        extracted = extract_job_appointments_from_raw(job.raw_detail_payload)
        if extracted:
            return job.raw_detail_payload
    if isinstance(raw_payload, dict):
        return raw_payload
    if isinstance(job.raw_payload, dict):
        return job.raw_payload
    return None


def is_cancelled_appointment_status(status: str | None) -> bool:
    if not status:
        return False
    normalized = status.strip().casefold()
    return any(marker in normalized for marker in _CANCELLED_STATUS_MARKERS)


def _parse_appointment_row(raw: dict[str, Any]) -> SafeJobAppointment | None:
    user_value = _pick_user_object(raw)
    user_id, user_name, user_email = _extract_user_fields(user_value)
    if not any((user_id, user_name, user_email)):
        return None

    appointment_id = _as_int(_pick(raw, "id", "appointment_id", "Appointment_ID", "Id"))
    appointment_type = _as_str(_pick(raw, *_APPOINTMENT_TYPE_KEYS), max_len=200)
    status = _as_str(_pick(raw, *_STATUS_KEYS), max_len=200)
    start_at = _extract_datetime(raw, start=True)
    end_at = _extract_datetime(raw, start=False)

    return {
        "appointment_id": appointment_id,
        "user_name": user_name,
        "user_email": user_email,
        "user_id": user_id,
        "appointment_type": appointment_type,
        "status": status,
        "start_at": start_at,
        "end_at": end_at,
    }


def extract_job_appointments_from_raw(raw_payload: dict[str, Any] | None) -> list[SafeJobAppointment]:
    """Return safe appointment rows extracted from a synced job payload."""
    appointments: list[SafeJobAppointment] = []
    for item in _appointment_list_from_raw(raw_payload):
        parsed = _parse_appointment_row(item)
        if parsed is not None:
            appointments.append(parsed)
    return appointments


def _appointment_sort_key(appointment: SafeJobAppointment) -> tuple[str, str]:
    return (appointment.get("start_at") or "", appointment.get("end_at") or "")


def _parse_sortable_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%b-%y %H:%M",
        "%d-%b-%Y %H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def select_active_appointment(appointments: list[SafeJobAppointment]) -> SafeJobAppointment | None:
    """Pick the active assignee appointment, ignoring cancelled rows."""
    active = [item for item in appointments if not is_cancelled_appointment_status(item.get("status"))]
    if not active:
        return None

    now = datetime.now(timezone.utc)
    upcoming = []
    for item in active:
        start_dt = _parse_sortable_datetime(item.get("start_at"))
        if start_dt is not None and start_dt >= now:
            upcoming.append((start_dt, item))
    if upcoming:
        upcoming.sort(key=lambda pair: pair[0])
        return upcoming[0][1]

    return sorted(active, key=_appointment_sort_key, reverse=True)[0]


def _build_dedupe_key(appointment: SafeJobAppointment) -> str:
    if appointment.get("appointment_id") is not None:
        return f"id:{appointment['appointment_id']}"
    return (
        "composite:"
        f"{(appointment.get('user_name') or '').casefold()}|"
        f"{appointment.get('start_at') or ''}|"
        f"{appointment.get('end_at') or ''}"
    )


def _build_safe_snapshot(appointment: SafeJobAppointment) -> dict[str, Any]:
    return {
        "appointment_id": appointment.get("appointment_id"),
        "user_name": appointment.get("user_name"),
        "user_email": appointment.get("user_email"),
        "user_id": appointment.get("user_id"),
        "appointment_type": appointment.get("appointment_type"),
        "status": appointment.get("status"),
        "start_at": appointment.get("start_at"),
        "end_at": appointment.get("end_at"),
    }


def sync_job_appointments(
    db: Session,
    job: EworksJob,
    *,
    raw_payload: dict[str, Any] | None = None,
    synced_at: datetime | None = None,
) -> EworksJobAppointment | None:
    """Upsert appointment rows for a job and refresh active assignee snapshot."""
    payload = raw_payload if isinstance(raw_payload, dict) else job.raw_payload
    source = appointment_source_payload(job, payload if isinstance(payload, dict) else None)
    synced = synced_at or datetime.now(timezone.utc)

    try:
        extracted = extract_job_appointments_from_raw(source if isinstance(source, dict) else None)
    except Exception:
        logger.exception("Failed to extract appointments for eWorks job id=%s", job.eworks_job_id)
        extracted = []

    seen_keys: set[str] = set()
    persisted: list[EworksJobAppointment] = []

    for appointment in extracted:
        dedupe_key = _build_dedupe_key(appointment)
        seen_keys.add(dedupe_key)
        existing = (
            db.query(EworksJobAppointment)
            .filter(
                EworksJobAppointment.eworks_job_id == job.eworks_job_id,
                EworksJobAppointment.dedupe_key == dedupe_key,
            )
            .one_or_none()
        )
        fields = {
            "appointment_id": appointment.get("appointment_id"),
            "job_ref": job.job_ref,
            "user_id": appointment.get("user_id"),
            "user_name": appointment.get("user_name"),
            "user_email": appointment.get("user_email"),
            "appointment_type": appointment.get("appointment_type"),
            "status": appointment.get("status"),
            "start_at": appointment.get("start_at"),
            "end_at": appointment.get("end_at"),
            "raw_safe_snapshot": _build_safe_snapshot(appointment),
            "synced_at": synced,
        }
        if existing is None:
            row = EworksJobAppointment(
                eworks_job_id=job.eworks_job_id,
                dedupe_key=dedupe_key,
                **fields,
            )
            db.add(row)
            db.flush()
            persisted.append(row)
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
            persisted.append(existing)

    stale_rows = (
        db.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .all()
    )
    for row in stale_rows:
        if row.dedupe_key not in seen_keys:
            db.delete(row)

    db.flush()

    active = select_active_appointment(extracted)
    active_row = None
    if active is not None:
        active_key = _build_dedupe_key(active)
        active_row = next((row for row in persisted if row.dedupe_key == active_key), None)
        if active_row is None:
            active_row = (
                db.query(EworksJobAppointment)
                .filter(
                    EworksJobAppointment.eworks_job_id == job.eworks_job_id,
                    EworksJobAppointment.dedupe_key == active_key,
                )
                .one_or_none()
            )

    job.active_appointment_id = active_row.id if active_row is not None else None
    job.assigned_user_name = active.get("user_name") if active else None
    job.assigned_user_email = active.get("user_email") if active else None
    job.assigned_user_id = active.get("user_id") if active else None
    job.next_appointment_at = active.get("start_at") if active else None
    db.flush()
    return active_row


def serialize_job_appointments(db: Session, job: EworksJob) -> list[dict[str, Any]]:
    rows = (
        db.query(EworksJobAppointment)
        .filter(EworksJobAppointment.eworks_job_id == job.eworks_job_id)
        .order_by(EworksJobAppointment.start_at.desc(), EworksJobAppointment.id.desc())
        .all()
    )
    return [
        {
            "appointment_id": row.appointment_id,
            "user_name": row.user_name,
            "user_email": row.user_email,
            "user_id": row.user_id,
            "appointment_type": row.appointment_type,
            "status": row.status,
            "start_at": row.start_at,
            "end_at": row.end_at,
            "is_active_assignment": row.id == job.active_appointment_id,
        }
        for row in rows
    ]
