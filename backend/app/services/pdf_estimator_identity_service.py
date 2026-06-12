"""Resolve estimator identity for PDFs and internal notes."""

from __future__ import annotations

import re

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.types import AuthenticatedUser
from app.models.calculation_session import CalculationSession
from app.models.user import User
from app.schemas.eworks_link import Step1Snapshot
from app.services.quote_assignment_service import _find_assignment_for_session, _is_unknown_submitter_name

_WHO_QUOTED_LINE = re.compile(r"^WHO QUOTED:.*$", re.MULTILINE)


def _resolved_name(name: str | None, email: str | None = None) -> str | None:
    cleaned = (name or "").strip()
    if cleaned and not _is_unknown_submitter_name(cleaned):
        return cleaned
    cleaned_email = (email or "").strip()
    return cleaned_email or None


def _user_display_name(user: User) -> str | None:
    return _resolved_name(user.full_name, user.email)


def _current_user_display_name(user: AuthenticatedUser) -> str | None:
    return _resolved_name(user.name, user.email)


def resolve_estimated_by_for_pdf(
    db: Session | None,
    session: CalculationSession | None,
    step1: Step1Snapshot | None = None,
    *,
    current_user: AuthenticatedUser | None = None,
) -> str:
    """
    Resolve the person who estimated/submitted the quote for PDF display.

    Priority:
    1. session.submitted_by_name
    2. session submitted_by user name/email
    3. assigned estimator/engineer for this calculation session
    4. current logged-in user generating/downloading PDF
    5. step1.engineer_name (eWorks/site data fallback only)
    """
    if session is not None:
        name = _resolved_name(session.submitted_by_name, session.submitted_by_email)
        if name:
            return name

        if db is not None and session.submitted_by_user_id is not None:
            user = db.get(User, session.submitted_by_user_id)
            if user is not None:
                user_name = _user_display_name(user)
                if user_name:
                    return user_name

        email_only = _resolved_name(None, session.submitted_by_email)
        if email_only:
            return email_only

        if db is not None:
            try:
                assignment = _find_assignment_for_session(db, session.id)
            except OperationalError:
                assignment = None
            if assignment is not None:
                assign_name = _resolved_name(assignment.assigned_user_name, assignment.assigned_user_email)
                if assign_name:
                    return assign_name

    if current_user is not None:
        current_name = _current_user_display_name(current_user)
        if current_name:
            return current_name

    if step1 is not None:
        fallback = (step1.engineer_name or "").strip()
        if fallback:
            return fallback

    return ""


def patch_who_quoted_in_internal_notes(notes: str | None, who_quoted: str) -> str | None:
    """Replace WHO QUOTED line in cached/generated internal notes with estimator identity."""
    if not notes:
        return notes
    name = (who_quoted or "").strip()
    if not name:
        return notes
    replacement = f"WHO QUOTED: {name}"
    if _WHO_QUOTED_LINE.search(notes):
        return _WHO_QUOTED_LINE.sub(replacement, notes)
    return notes
