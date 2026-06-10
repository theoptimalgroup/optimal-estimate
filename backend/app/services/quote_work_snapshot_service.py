"""Shared quote-level Step 2 work block snapshots for estimation forms."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.core.exceptions import AppError
from app.core.security import UserRole
from app.models.calculation_session import CalculationSession
from app.models.quote_work_snapshot import QuoteWorkSnapshot
from app.schemas.eworks_link import SharedStep2Meta, Step2Snapshot, WorkBlockSnapshot
from app.utils.html_text import html_to_plain_text
from app.services.quote_assignment_service import _as_uuid, _normalize_email
from app.services.quote_work_attachment_service import (
    _user_assigned_to_quote,
    merge_shared_attachments_into_step2,
    resolve_session_quote_keys,
)

if TYPE_CHECKING:
    pass

CUSTOM_SCOPE_TITLE_MAX = 80


def _work_block_has_product_context(block: WorkBlockSnapshot) -> bool:
    if block.is_custom_scope:
        return bool((block.custom_title or "").strip())
    return (
        block.selected_product_id is not None
        or block.eworks_item_id is not None
        or bool((block.product_name or "").strip())
    )


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _work_block_meaningful_scope_text(block: WorkBlockSnapshot) -> str | None:
    for candidate in (block.scope, block.custom_title, block.product_name):
        text = html_to_plain_text(candidate).strip() if candidate else ""
        if text:
            return text
    return None


def _derive_custom_scope_title(block: WorkBlockSnapshot) -> str:
    scope = _work_block_meaningful_scope_text(block)
    if not scope:
        return "Custom scope"
    collapsed = _collapse_whitespace(scope)
    if len(collapsed) > CUSTOM_SCOPE_TITLE_MAX:
        return f"{collapsed[:CUSTOM_SCOPE_TITLE_MAX]}…"
    return collapsed


def _normalize_work_block_scope_to_custom(block: WorkBlockSnapshot) -> WorkBlockSnapshot:
    if _work_block_has_product_context(block):
        return block
    if not _work_block_meaningful_scope_text(block):
        return block
    title = _derive_custom_scope_title(block)
    return block.model_copy(
        update={
            "is_custom_scope": True,
            "custom_title": title,
            "product_name": title,
            "selected_product_id": None,
            "eworks_item_id": None,
        }
    )


def normalize_shared_work_blocks(step2: Step2Snapshot) -> Step2Snapshot:
    """Treat scope-only shared work blocks as custom scope for validation and display."""
    normalized = Step2Snapshot.model_validate(step2.model_dump(mode="json"))
    if not normalized.works:
        return normalized
    works = [_normalize_work_block_scope_to_custom(block) for block in normalized.works]
    return normalized.model_copy(update={"works": works})


def _snapshot_quote_filter(quote_ref: str | None, eworks_quote_id: int | None):
    clauses = []
    if eworks_quote_id is not None:
        clauses.append(QuoteWorkSnapshot.eworks_quote_id == eworks_quote_id)
    if quote_ref:
        clauses.append(QuoteWorkSnapshot.quote_ref == quote_ref)
    if not clauses:
        return None
    return or_(*clauses) if len(clauses) > 1 else clauses[0]


def strip_attachments_from_step2(step2: Step2Snapshot) -> Step2Snapshot:
    """Shared snapshots store work blocks only; attachments live in quote_work_attachments."""
    works = [block.model_copy(update={"attachments": []}) for block in step2.works]
    return step2.model_copy(
        update={
            "works": works,
            "attachments": [],
            "unmatched_attachments": [],
        }
    )


def get_quote_work_snapshot(
    db: Session,
    *,
    quote_ref: str | None,
    eworks_quote_id: int | None,
) -> QuoteWorkSnapshot | None:
    clause = _snapshot_quote_filter(quote_ref, eworks_quote_id)
    if clause is None:
        return None
    return db.scalar(select(QuoteWorkSnapshot).where(clause).limit(1))


def _snapshot_meta(row: QuoteWorkSnapshot) -> SharedStep2Meta:
    return SharedStep2Meta(
        updated_by_name=row.updated_by_name,
        updated_by_email=row.updated_by_email,
        updated_at=row.updated_at,
        version=row.version,
    )


def user_can_access_quote_work_snapshot(
    db: Session,
    *,
    user: AuthenticatedUser | None,
    quote_ref: str | None,
    eworks_quote_id: int | None,
    synced_quote_id: int | None,
    session: CalculationSession | None = None,
) -> bool:
    if user is not None and user.role in {UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR}:
        if user.role in {UserRole.ADMIN, UserRole.MANAGER}:
            return True
        if _user_assigned_to_quote(
            db,
            user,
            quote_ref=quote_ref,
            eworks_quote_id=eworks_quote_id,
            synced_quote_id=synced_quote_id,
        ):
            return True
    if user is not None and user.role == UserRole.ENGINEER:
        return _user_assigned_to_quote(
            db,
            user,
            quote_ref=quote_ref,
            eworks_quote_id=eworks_quote_id,
            synced_quote_id=synced_quote_id,
        )
    if session is not None:
        session_ref, session_eworks_id, session_synced_id = resolve_session_quote_keys(session)
        if eworks_quote_id is not None and session_eworks_id == eworks_quote_id:
            return True
        if quote_ref and session_ref and session_ref == quote_ref:
            return True
        if synced_quote_id is not None and session_synced_id == synced_quote_id:
            return True
    return False


def _find_sessions_for_quote(
    db: Session,
    *,
    quote_ref: str | None,
    eworks_quote_id: int | None,
) -> list[CalculationSession]:
    if quote_ref is None and eworks_quote_id is None:
        return []

    sessions = db.scalars(
        select(CalculationSession).where(CalculationSession.step2_snapshot.isnot(None))
    ).all()
    matched: list[CalculationSession] = []
    for session in sessions:
        session_ref, session_eworks_id, _ = resolve_session_quote_keys(session)
        if eworks_quote_id is not None and session_eworks_id == eworks_quote_id:
            matched.append(session)
        elif quote_ref and session_ref == quote_ref:
            matched.append(session)
    return matched


def _resolve_actor_identity(
    db: Session,
    session: CalculationSession,
    actor: AuthenticatedUser | None,
) -> tuple[UUID | None, str | None, str | None]:
    if actor is not None:
        return _as_uuid(actor.id), actor.name, actor.email

    from app.services.calculation_session_revision_service import resolve_session_submitter

    return resolve_session_submitter(db, session)


def seed_shared_step2_from_sessions(
    db: Session,
    session: CalculationSession,
    *,
    actor: AuthenticatedUser | None = None,
) -> QuoteWorkSnapshot | None:
    quote_ref, eworks_quote_id, synced_quote_id = resolve_session_quote_keys(session)
    if quote_ref is None and eworks_quote_id is None:
        return None

    existing = get_quote_work_snapshot(db, quote_ref=quote_ref, eworks_quote_id=eworks_quote_id)
    if existing is not None:
        return existing

    candidates = _find_sessions_for_quote(db, quote_ref=quote_ref, eworks_quote_id=eworks_quote_id)
    source = session
    best_updated: datetime | None = None
    for candidate in candidates:
        if not candidate.step2_snapshot:
            continue
        updated = candidate.updated_at or candidate.created_at
        if best_updated is None or updated > best_updated:
            source = candidate
            best_updated = updated

    if not source.step2_snapshot:
        step2 = Step2Snapshot()
    else:
        step2 = normalize_shared_work_blocks(Step2Snapshot.model_validate(source.step2_snapshot))

    user_id, name, email = _resolve_actor_identity(db, source, actor)
    row = QuoteWorkSnapshot(
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
        synced_quote_id=synced_quote_id,
        step2_snapshot=strip_attachments_from_step2(step2).model_dump(mode="json"),
        version=1,
        updated_by_user_id=user_id,
        updated_by_name=name,
        updated_by_email=email,
    )
    db.add(row)
    db.flush()
    return row


def save_shared_step2(
    db: Session,
    session: CalculationSession,
    step2: Step2Snapshot,
    *,
    actor: AuthenticatedUser | None = None,
) -> QuoteWorkSnapshot:
    quote_ref, eworks_quote_id, synced_quote_id = resolve_session_quote_keys(session)
    if quote_ref is None and eworks_quote_id is None:
        raise AppError("QUOTE_IDENTITY_MISSING", "Cannot save shared work plan without quote identity", 400)

    if actor is not None and not user_can_access_quote_work_snapshot(
        db,
        user=actor,
        quote_ref=quote_ref,
        eworks_quote_id=eworks_quote_id,
        synced_quote_id=synced_quote_id,
        session=session,
    ):
        raise AppError("QUOTE_WORK_FORBIDDEN", "You are not assigned to this quote", 403)

    stripped = strip_attachments_from_step2(normalize_shared_work_blocks(step2))
    user_id, name, email = _resolve_actor_identity(db, session, actor)

    row = get_quote_work_snapshot(db, quote_ref=quote_ref, eworks_quote_id=eworks_quote_id)
    if row is None:
        row = QuoteWorkSnapshot(
            quote_ref=quote_ref,
            eworks_quote_id=eworks_quote_id,
            synced_quote_id=synced_quote_id,
            step2_snapshot=stripped.model_dump(mode="json"),
            version=1,
            updated_by_user_id=user_id,
            updated_by_name=name,
            updated_by_email=email,
        )
        db.add(row)
    else:
        row.step2_snapshot = stripped.model_dump(mode="json")
        row.version = (row.version or 0) + 1
        row.updated_by_user_id = user_id
        row.updated_by_name = name
        row.updated_by_email = email
        row.updated_at = datetime.now(timezone.utc)
        if synced_quote_id is not None:
            row.synced_quote_id = synced_quote_id

    db.flush()
    return row


def _merge_legacy_session_attachments(session: CalculationSession, step2: Step2Snapshot) -> Step2Snapshot:
    """Preserve session-only attachments not yet migrated to quote_work_attachments."""
    if not session.step2_snapshot:
        return step2
    session_step2 = Step2Snapshot.model_validate(session.step2_snapshot)
    if not session_step2.works:
        return step2

    works: list = []
    for index, block in enumerate(step2.works):
        existing_ids = {attachment.id for attachment in block.attachments}
        legacy_block = session_step2.works[index] if index < len(session_step2.works) else None
        extras = []
        if legacy_block is not None:
            for attachment in legacy_block.attachments:
                if attachment.id not in existing_ids:
                    extras.append(attachment)
        if extras:
            block = block.model_copy(update={"attachments": [*block.attachments, *extras]})
        works.append(block)
    return step2.model_copy(update={"works": works})


def resolve_shared_step2_for_session(
    db: Session,
    session: CalculationSession,
    *,
    actor: AuthenticatedUser | None = None,
) -> tuple[Step2Snapshot | None, SharedStep2Meta | None]:
    quote_ref, eworks_quote_id, synced_quote_id = resolve_session_quote_keys(session)
    if quote_ref is None and eworks_quote_id is None:
        step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
        if step2 is not None:
            step2 = normalize_shared_work_blocks(step2)
            step2 = merge_shared_attachments_into_step2(db, session, step2)
        return step2, None

    row = get_quote_work_snapshot(db, quote_ref=quote_ref, eworks_quote_id=eworks_quote_id)
    if row is None:
        row = seed_shared_step2_from_sessions(db, session, actor=actor)

    if row is None:
        step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
        if step2 is not None:
            step2 = normalize_shared_work_blocks(step2)
            step2 = merge_shared_attachments_into_step2(db, session, step2)
        return step2, None

    step2 = normalize_shared_work_blocks(Step2Snapshot.model_validate(row.step2_snapshot))
    step2 = merge_shared_attachments_into_step2(db, session, step2)
    step2 = _merge_legacy_session_attachments(session, step2)
    return step2, _snapshot_meta(row)


def sync_session_step2_from_shared(
    db: Session,
    session: CalculationSession,
    step2: Step2Snapshot,
) -> None:
    """Keep session snapshot aligned with shared work plan (attachments remain session-local until merge)."""
    session.step2_snapshot = step2.model_dump(mode="json")
