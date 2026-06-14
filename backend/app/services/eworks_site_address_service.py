"""Resolve eWorks site/property addresses from synced quote and job data."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksQuote
from app.models.quote_assignment import EworksQuoteAssignment
from app.schemas.eworks_link import Step1Snapshot

PLACEHOLDER_PROPERTY_ADDRESSES = frozenset(
    {
        "address not specified",
        "not specified",
        "unknown",
        "n/a",
    }
)


def _as_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def is_missing_or_placeholder_address(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    return text.lower() in PLACEHOLDER_PROPERTY_ADDRESSES


def _join_unique_parts(parts: list[str]) -> str | None:
    ordered: list[str] = []
    seen: set[str] = set()
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ", ".join(ordered) if ordered else None


def _parts_from_site_dict(site: dict[str, Any]) -> list[str]:
    line_parts = [
        _as_str(site.get("address_1") or site.get("address1") or site.get("address")),
        _as_str(site.get("address_2") or site.get("address2")),
    ]
    line = ", ".join(part for part in line_parts if part)
    parts: list[str] = []
    if line:
        parts.append(line)
    else:
        for key in ("site_address", "name"):
            val = _as_str(site.get(key))
            if val:
                parts.append(val)
                break
    line_lower = line.casefold() if line else ""
    for key in ("city", "county", "postcode", "zip"):
        val = _as_str(site.get(key))
        if val and val.casefold() not in line_lower:
            parts.append(val)
    return parts


def extract_site_address_from_raw(raw: dict[str, Any] | None) -> str | None:
    """Build a one-line site address from quote/job raw payload fields."""
    if not isinstance(raw, dict):
        return None

    for nested_key in ("site", "Site", "customer_site", "Customer_Site"):
        nested = raw.get(nested_key)
        if isinstance(nested, dict):
            joined = _join_unique_parts(_parts_from_site_dict(nested))
            if joined:
                return joined

    flat_parts: list[str] = []
    for key in ("site_address", "address", "address_1", "Address_1"):
        val = _as_str(raw.get(key))
        if val:
            flat_parts.append(val)
    city = _as_str(raw.get("city"))
    postcode = _as_str(raw.get("postcode"))
    if city:
        flat_parts.append(city)
    if postcode:
        flat_parts.append(postcode)
    return _join_unique_parts(flat_parts)


def extract_site_address_from_quote(quote: EworksQuote) -> str | None:
    raw = quote.raw_payload if isinstance(quote.raw_payload, dict) else {}
    resolved = extract_site_address_from_raw(raw)
    if resolved:
        return resolved
    return None


def extract_site_address_from_job(job: EworksJob) -> str | None:
    address = _as_str(job.address)
    if address and not is_missing_or_placeholder_address(address):
        return address
    raw = job.raw_payload if isinstance(job.raw_payload, dict) else {}
    detail = job.raw_detail_payload if isinstance(job.raw_detail_payload, dict) else {}
    for payload in (detail, raw):
        resolved = extract_site_address_from_raw(payload)
        if resolved:
            return resolved
    return None


def _find_linked_job_for_quote(db: Session, quote: EworksQuote) -> EworksJob | None:
    return db.scalar(
        select(EworksJob)
        .where(EworksJob.eworks_quote_id == quote.eworks_quote_id)
        .order_by(EworksJob.synced_at.desc(), EworksJob.id.desc())
        .limit(1)
    )


def find_synced_quote_for_session(db: Session, session: CalculationSession) -> EworksQuote | None:
    payload = session.payload_snapshot if isinstance(session.payload_snapshot, dict) else {}

    synced_quote_id = payload.get("synced_quote_id")
    if synced_quote_id is not None:
        try:
            quote = db.get(EworksQuote, int(synced_quote_id))
            if quote is not None:
                return quote
        except (TypeError, ValueError):
            pass

    assignment_id = payload.get("assignment_id")
    if assignment_id is not None:
        try:
            assignment = db.get(EworksQuoteAssignment, int(assignment_id))
            if assignment is not None:
                quote = db.get(EworksQuote, assignment.synced_quote_id)
                if quote is not None:
                    return quote
        except (TypeError, ValueError):
            pass

    eworks_quote_id = payload.get("eworks_quote_id")
    if eworks_quote_id is not None:
        try:
            return db.scalar(
                select(EworksQuote)
                .where(EworksQuote.eworks_quote_id == int(eworks_quote_id))
                .order_by(EworksQuote.synced_at.desc(), EworksQuote.id.desc())
                .limit(1)
            )
        except (TypeError, ValueError):
            pass

    assignment = db.scalar(
        select(EworksQuoteAssignment)
        .where(EworksQuoteAssignment.calculation_session_id == session.id)
        .order_by(EworksQuoteAssignment.id.desc())
        .limit(1)
    )
    if assignment is not None:
        return db.get(EworksQuote, assignment.synced_quote_id)
    return None


def resolve_site_address_for_quote(db: Session, quote: EworksQuote) -> str | None:
    resolved = extract_site_address_from_quote(quote)
    if resolved:
        return resolved
    job = _find_linked_job_for_quote(db, quote)
    if job is not None:
        return extract_site_address_from_job(job)
    return None


def resolve_site_address_for_session(db: Session, session: CalculationSession) -> str | None:
    quote = find_synced_quote_for_session(db, session)
    if quote is None:
        return None
    return resolve_site_address_for_quote(db, quote)


def resolve_display_property_address(
    db: Session | None,
    session: CalculationSession | None,
    step1: Step1Snapshot,
) -> str:
    """Return a display-safe property address; never a placeholder string."""
    current = (step1.property_address or "").strip()
    if current and not is_missing_or_placeholder_address(current):
        return current
    if db is not None and session is not None:
        refreshed = resolve_site_address_for_session(db, session)
        if refreshed:
            return refreshed
    return ""


def resolve_step1_for_display(
    db: Session | None,
    session: CalculationSession | None,
    step1: Step1Snapshot,
) -> Step1Snapshot:
    resolved = resolve_display_property_address(db, session, step1)
    if resolved == (step1.property_address or "").strip():
        return step1
    return step1.model_copy(update={"property_address": resolved})


def maybe_refresh_step1_property_address(db: Session, session: CalculationSession) -> bool:
    """Persist a refreshed property address when snapshot holds a placeholder."""
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    if not is_missing_or_placeholder_address(step1.property_address):
        return False
    refreshed = resolve_site_address_for_session(db, session)
    if not refreshed:
        if is_missing_or_placeholder_address(step1.property_address):
            session.step1_snapshot = step1.model_copy(update={"property_address": ""}).model_dump(mode="json")
            return True
        return False
    session.step1_snapshot = step1.model_copy(update={"property_address": refreshed}).model_dump(mode="json")
    return True
