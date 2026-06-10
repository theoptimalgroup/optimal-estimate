"""Shared quote-level work block attachments for estimation forms."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.exceptions import AppError
from app.core.security import UserRole
from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuoteAppointment
from app.models.quote_assignment import EworksQuoteAssignment
from app.models.quote_work_attachment import QuoteWorkAttachment
from app.schemas.eworks_link import SessionAttachmentMeta, Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.eworks_acceptance_sync_service import resolve_eworks_quote_id
from app.services.quote_assignment_service import _as_uuid, _normalize_email
from app.utils.work_label import format_work_label

if TYPE_CHECKING:
    from fastapi import UploadFile

logger = logging.getLogger(__name__)


def extract_work_block_context(block: WorkBlockSnapshot, work_index: int) -> dict:
    """Capture frozen product/scope context from a work block at upload time."""
    if block.is_custom_scope:
        custom_title = (block.custom_title or block.product_name or "").strip() or None
        product_name = custom_title
    else:
        custom_title = None
        product_name = (block.product_name or "").strip() or None

    return {
        "product_id": block.selected_product_id,
        "product_name": product_name,
        "is_custom_scope": block.is_custom_scope,
        "custom_scope_title": custom_title,
        "scope_snapshot": (block.scope or "").strip() or None,
        "work_block_label": format_work_label(
            product_name=block.product_name,
            product_code=block.product_code,
            scope=block.scope,
            index=work_index,
            is_custom_scope=block.is_custom_scope,
            custom_title=block.custom_title,
        ),
    }


def _work_block_from_session(session: CalculationSession, work_index: int) -> WorkBlockSnapshot | None:
    if not session.step2_snapshot:
        return None
    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    if work_index < 0 or work_index >= len(step2.works):
        return None
    return step2.works[work_index]


def resolve_session_quote_keys(session: CalculationSession) -> tuple[str | None, int | None, int | None]:
    """Return (quote_ref, eworks_quote_id, synced_quote_id) for a calculation session."""
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    payload = session.payload_snapshot if isinstance(session.payload_snapshot, dict) else {}

    eworks_quote_id = resolve_eworks_quote_id(session)
    quote_ref = (step1.quote_number or payload.get("quote_number") or "").strip() or None

    synced_quote_id = payload.get("synced_quote_id")
    if synced_quote_id is not None:
        try:
            synced_quote_id = int(synced_quote_id)
        except (TypeError, ValueError):
            synced_quote_id = None

    if eworks_quote_id is not None and quote_ref is None:
        quote_ref = f"Q{eworks_quote_id}"

    return quote_ref, eworks_quote_id, synced_quote_id


def _quote_filter(quote_ref: str | None, eworks_quote_id: int | None):
    clauses = []
    if eworks_quote_id is not None:
        clauses.append(QuoteWorkAttachment.eworks_quote_id == eworks_quote_id)
    if quote_ref:
        clauses.append(QuoteWorkAttachment.quote_ref == quote_ref)
    if not clauses:
        return None
    return or_(*clauses) if len(clauses) > 1 else clauses[0]


def _session_matches_quote(
    session: CalculationSession,
    *,
    quote_ref: str | None,
    eworks_quote_id: int | None,
) -> bool:
    session_ref, session_eworks_id, _ = resolve_session_quote_keys(session)
    if eworks_quote_id is not None and session_eworks_id == eworks_quote_id:
        return True
    if quote_ref and session_ref and session_ref == quote_ref:
        return True
    return False


def _user_assigned_to_quote(
    db: Session,
    user: AuthenticatedUser,
    *,
    quote_ref: str | None,
    eworks_quote_id: int | None,
    synced_quote_id: int | None,
) -> bool:
    user_id = _as_uuid(user.id)
    user_email = _normalize_email(user.email)

    assignment_filters = [EworksQuoteAssignment.status != "cancelled"]
    if synced_quote_id is not None:
        assignment_filters.append(EworksQuoteAssignment.synced_quote_id == synced_quote_id)
    elif eworks_quote_id is not None:
        assignment_filters.append(EworksQuoteAssignment.eworks_quote_id == eworks_quote_id)
    elif quote_ref:
        assignment_filters.append(EworksQuoteAssignment.quote_ref == quote_ref)
    else:
        return False

    if user_id is not None:
        assignment_filters.append(EworksQuoteAssignment.assigned_user_id == user_id)
        if db.scalar(select(EworksQuoteAssignment.id).where(*assignment_filters).limit(1)):
            return True

    if user_email:
        email_filters = list(assignment_filters)
        email_filters.append(EworksQuoteAssignment.assigned_user_id.is_(None))
        email_filters.append(EworksQuoteAssignment.assigned_user_email.isnot(None))
        rows = db.scalars(select(EworksQuoteAssignment).where(*email_filters)).all()
        for row in rows:
            if _normalize_email(row.assigned_user_email) == user_email:
                return True

    if eworks_quote_id is None:
        return False

    from app.services.engineer_assigned_estimates_service import _appointment_user_matches
    from app.services.engineer_assignment_routing import is_quote_linked_assignment
    from app.services.eworks_job_appointment_service import is_cancelled_appointment_status

    job_rows = (
        db.query(EworksJob, EworksJobAppointment)
        .join(EworksJobAppointment, EworksJob.active_appointment_id == EworksJobAppointment.id)
        .filter(EworksJob.eworks_quote_id == eworks_quote_id)
        .all()
    )
    for job, appointment in job_rows:
        if is_cancelled_appointment_status(appointment.status):
            continue
        if not is_quote_linked_assignment(db, job, appointment):
            continue
        if _appointment_user_matches(db, appointment, user=user):
            return True

    quote_rows = (
        db.query(EworksQuoteAppointment)
        .filter(EworksQuoteAppointment.eworks_quote_id == eworks_quote_id)
        .all()
    )
    for appointment in quote_rows:
        if is_cancelled_appointment_status(appointment.status):
            continue
        if _appointment_user_matches(db, appointment, user=user):
            return True

    return False


def user_can_view_quote_attachment(
    db: Session,
    *,
    user: AuthenticatedUser | None,
    attachment: QuoteWorkAttachment,
    session: CalculationSession | None = None,
) -> bool:
    if user is not None and user.role in {UserRole.ADMIN, UserRole.MANAGER}:
        return True
    if user is not None and _user_assigned_to_quote(
        db,
        user,
        quote_ref=attachment.quote_ref,
        eworks_quote_id=attachment.eworks_quote_id,
        synced_quote_id=attachment.synced_quote_id,
    ):
        return True
    if session is not None and _session_matches_quote(
        session,
        quote_ref=attachment.quote_ref,
        eworks_quote_id=attachment.eworks_quote_id,
    ):
        return True
    return False


def user_can_delete_quote_attachment(
    db: Session,
    *,
    user: AuthenticatedUser | None,
    attachment: QuoteWorkAttachment,
    session: CalculationSession | None = None,
) -> bool:
    if user is not None and user.role in {UserRole.ADMIN, UserRole.MANAGER}:
        return True

    from app.services.calculation_session_revision_service import resolve_session_submitter

    actor_user_id: UUID | None = None
    actor_email: str | None = None
    if user is not None:
        actor_user_id = _as_uuid(user.id)
        actor_email = _normalize_email(user.email)
    elif session is not None:
        actor_user_id, _, actor_email_raw = resolve_session_submitter(db, session)
        actor_email = _normalize_email(actor_email_raw)

    if actor_user_id is not None and attachment.uploaded_by_user_id == actor_user_id:
        return True
    if actor_email and attachment.uploaded_by_email:
        return actor_email == _normalize_email(attachment.uploaded_by_email)
    return False


def get_quote_attachment_row(db: Session, attachment_id: str) -> QuoteWorkAttachment | None:
    return db.scalar(select(QuoteWorkAttachment).where(QuoteWorkAttachment.attachment_id == attachment_id))


def list_quote_work_attachments(
    db: Session,
    *,
    quote_ref: str | None,
    eworks_quote_id: int | None,
    work_index: int | None = None,
) -> list[QuoteWorkAttachment]:
    clause = _quote_filter(quote_ref, eworks_quote_id)
    if clause is None:
        return []
    query = select(QuoteWorkAttachment).where(clause).order_by(QuoteWorkAttachment.created_at.asc())
    if work_index is not None:
        query = query.where(QuoteWorkAttachment.work_index == work_index)
    return list(db.scalars(query).all())


def row_to_meta(row: QuoteWorkAttachment) -> SessionAttachmentMeta:
    return SessionAttachmentMeta(
        id=row.attachment_id,
        file_name=row.file_name,
        content_type=row.content_type,
        size=row.size,
        media_type=row.media_type,
        stored_name=row.stored_name,
        uploaded_by_name=row.uploaded_by_name,
        uploaded_by_email=row.uploaded_by_email,
        uploaded_at=row.created_at,
        work_index=row.work_index,
        product_id=row.product_id,
        product_name=row.product_name,
        is_custom_scope=row.is_custom_scope,
        custom_scope_title=row.custom_scope_title,
        scope_snapshot=row.scope_snapshot,
        work_block_label=row.work_block_label,
    )


def merge_shared_attachments_into_step2(db: Session, session: CalculationSession, step2: Step2Snapshot) -> Step2Snapshot:
    quote_ref, eworks_quote_id, _ = resolve_session_quote_keys(session)
    if quote_ref is None and eworks_quote_id is None:
        return step2

    shared_rows = list_quote_work_attachments(db, quote_ref=quote_ref, eworks_quote_id=eworks_quote_id)
    if not shared_rows:
        return step2

    by_work: dict[int, list[SessionAttachmentMeta]] = {}
    unmatched: list[SessionAttachmentMeta] = []
    work_count = len(step2.works)

    for row in shared_rows:
        meta = row_to_meta(row)
        if work_count == 0 or row.work_index < 0 or row.work_index >= work_count:
            unmatched.append(meta)
            continue
        by_work.setdefault(row.work_index, []).append(meta)

    if unmatched:
        logger.warning(
            "Unmatched quote work attachments for quote_ref=%s eworks_quote_id=%s count=%d",
            quote_ref,
            eworks_quote_id,
            len(unmatched),
        )

    if not step2.works and not by_work:
        return step2.model_copy(update={"unmatched_attachments": unmatched})

    if not step2.works:
        step2 = Step2Snapshot.model_validate({"scope": step2.scope, **step2.model_dump()})

    merged_works = []
    for index, block in enumerate(step2.works):
        shared = by_work.get(index, [])
        if not shared:
            merged_works.append(block)
            continue
        existing_ids = {item.id for item in block.attachments}
        attachments = list(block.attachments)
        for meta in shared:
            if meta.id not in existing_ids:
                attachments.append(meta)
                existing_ids.add(meta.id)
        merged_works.append(block.model_copy(update={"attachments": attachments}))

    return step2.model_copy(update={"works": merged_works, "unmatched_attachments": unmatched})


def resolve_uploader(
    db: Session,
    session: CalculationSession,
    actor: AuthenticatedUser | None,
) -> tuple[UUID | None, str | None, str | None]:
    if actor is not None:
        return _as_uuid(actor.id), actor.name, actor.email

    from app.services.calculation_session_revision_service import resolve_session_submitter

    return resolve_session_submitter(db, session)


async def save_quote_work_attachment(
    db: Session,
    *,
    session: CalculationSession,
    upload: UploadFile,
    work_index: int,
    actor: AuthenticatedUser | None = None,
) -> SessionAttachmentMeta:
    from app.services.eworks_attachment_service import save_session_attachment

    quote_ref, eworks_quote_id, synced_quote_id = resolve_session_quote_keys(session)

    attachment = await save_session_attachment(session.id, upload, eworks_quote_id=eworks_quote_id)
    existing = get_quote_attachment_row(db, attachment.id)
    if existing is not None:
        return row_to_meta(existing)

    uploaded_by_user_id, uploaded_by_name, uploaded_by_email = resolve_uploader(db, session, actor)
    block = _work_block_from_session(session, work_index)
    context = extract_work_block_context(block, work_index) if block is not None else {}

    row = QuoteWorkAttachment(
        attachment_id=attachment.id,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
        synced_quote_id=synced_quote_id,
        work_index=work_index,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size=attachment.size,
        media_type=attachment.media_type,
        stored_name=attachment.stored_name,
        storage_session_id=session.id,
        uploaded_by_user_id=uploaded_by_user_id,
        uploaded_by_email=uploaded_by_email,
        uploaded_by_name=uploaded_by_name,
        source_session_id=session.id,
        **context,
    )
    db.add(row)
    db.flush()

    meta = row_to_meta(row)
    return meta.model_copy(
        update={
            "uploaded_by_name": uploaded_by_name,
            "uploaded_by_email": uploaded_by_email,
            "uploaded_at": row.created_at,
            "work_index": work_index,
        }
    )


def register_legacy_attachment(
    db: Session,
    *,
    session: CalculationSession,
    work_index: int,
    attachment: SessionAttachmentMeta,
    actor: AuthenticatedUser | None = None,
) -> QuoteWorkAttachment | None:
    quote_ref, eworks_quote_id, synced_quote_id = resolve_session_quote_keys(session)
    if quote_ref is None and eworks_quote_id is None:
        return None

    existing = get_quote_attachment_row(db, attachment.id)
    if existing is not None:
        return existing

    uploaded_by_user_id, uploaded_by_name, uploaded_by_email = resolve_uploader(db, session, actor)
    block = _work_block_from_session(session, work_index)
    context = extract_work_block_context(block, work_index) if block is not None else {}

    row = QuoteWorkAttachment(
        attachment_id=attachment.id,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
        synced_quote_id=synced_quote_id,
        work_index=work_index,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size=attachment.size,
        media_type=attachment.media_type,
        stored_name=attachment.stored_name,
        storage_session_id=session.id,
        uploaded_by_user_id=uploaded_by_user_id,
        uploaded_by_email=uploaded_by_email,
        uploaded_by_name=uploaded_by_name,
        source_session_id=session.id,
        **context,
    )
    db.add(row)
    db.flush()
    return row


async def delete_quote_work_attachment(
    db: Session,
    *,
    attachment_id: str,
    session: CalculationSession | None = None,
    actor: AuthenticatedUser | None = None,
) -> QuoteWorkAttachment:
    from app.services.eworks_attachment_service import delete_stored_attachment

    row = get_quote_attachment_row(db, attachment_id)
    if row is None:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)

    if not user_can_delete_quote_attachment(db, user=actor, attachment=row, session=session):
        raise AppError("ATTACHMENT_FORBIDDEN", "Insufficient permissions to delete attachment", 403)

    storage_session_id = row.storage_session_id or row.source_session_id
    if storage_session_id is not None:
        await delete_stored_attachment(
            storage_session_id,
            row.stored_name,
            eworks_quote_id=row.eworks_quote_id,
        )

    db.delete(row)
    db.flush()
    return row


def resolve_attachment_meta(
    db: Session,
    session_id: UUID,
    attachment_id: str,
) -> tuple[SessionAttachmentMeta, QuoteWorkAttachment | None, CalculationSession | None]:
    session = db.get(CalculationSession, session_id)
    row = get_quote_attachment_row(db, attachment_id)
    if row is not None:
        return row_to_meta(row), row, session

    if session is None or not session.step2_snapshot:
        raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)

    step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    for work_index, block in enumerate(step2.works):
        for attachment in block.attachments:
            if attachment.id == attachment_id:
                register_legacy_attachment(
                    db,
                    session=session,
                    work_index=work_index,
                    attachment=SessionAttachmentMeta.model_validate(attachment),
                )
                refreshed = get_quote_attachment_row(db, attachment_id)
                if refreshed is not None:
                    return row_to_meta(refreshed), refreshed, session
                return SessionAttachmentMeta.model_validate(attachment), None, session
    for attachment in step2.attachments:
        if attachment.id == attachment_id:
            return SessionAttachmentMeta.model_validate(attachment), None, session

    raise AppError("ATTACHMENT_NOT_FOUND", "Attachment not found", 404)


def backfill_attachments_from_sessions(db: Session) -> int:
    """Register legacy session step2 attachments into quote_work_attachments."""
    count = 0
    sessions = db.scalars(select(CalculationSession).where(CalculationSession.step2_snapshot.isnot(None))).all()
    for session in sessions:
        quote_ref, eworks_quote_id, _ = resolve_session_quote_keys(session)
        if quote_ref is None and eworks_quote_id is None:
            continue
        step2 = Step2Snapshot.model_validate(session.step2_snapshot)
        for work_index, block in enumerate(step2.works):
            for attachment in block.attachments:
                meta = SessionAttachmentMeta.model_validate(attachment)
                if get_quote_attachment_row(db, meta.id) is not None:
                    continue
                register_legacy_attachment(db, session=session, work_index=work_index, attachment=meta)
                count += 1
    return count
