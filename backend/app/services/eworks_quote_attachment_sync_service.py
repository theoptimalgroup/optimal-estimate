"""Fetch eWorks quote attachments from detail/attachment endpoints and sync locally."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.eworks_sync import EworksQuote
from app.services.eworks_attachment_sync_service import (
    find_attachment_like_keys,
    payload_has_embedded_attachments,
    sync_parent_attachment_items,
    sync_parent_attachments_detailed,
)
from app.services.eworks_quotes_jobs_api_service import fetch_quote_attachments, fetch_quote_detail

logger = logging.getLogger(__name__)

QUOTE_ATTACHMENT_ENDPOINT = "GET /Quote/{id}/Attachments"
QUOTE_DETAIL_ENDPOINT = "GET /Quote/{id}"


@dataclass
class QuoteAttachmentSyncResult:
    endpoint_called: str | None = None
    attachment_keys_found: list[str] | None = None
    attachments_extracted: int = 0
    attachments_created: int = 0
    attachments_updated: int = 0
    detail_fetched: bool = False
    attachment_endpoint_called: bool = False
    failed: bool = False


@dataclass
class QuoteAttachmentBackfillSummary:
    quotes_scanned: int = 0
    details_fetched: int = 0
    attachment_endpoint_calls: int = 0
    quotes_with_attachments: int = 0
    attachments_created: int = 0
    attachments_updated: int = 0
    failed: int = 0


def _log_quote_attachment_attempt(
    *,
    quote_ref: str | None,
    eworks_quote_id: int,
    endpoint_called: str | None,
    attachment_keys_found: list[str],
    attachments_extracted: int,
) -> None:
    logger.info(
        "eWorks quote attachments: quote_ref=%s eworks_quote_id=%s endpoint=%s "
        "attachment_keys_found=%s attachments_extracted=%s",
        quote_ref or "—",
        eworks_quote_id,
        endpoint_called or "none",
        attachment_keys_found or [],
        attachments_extracted,
    )


def sync_quote_attachments_from_eworks(
    db: Session,
    quote: EworksQuote,
    *,
    fetch_detail_if_needed: bool = True,
) -> QuoteAttachmentSyncResult:
    """Fetch quote attachments from eWorks and upsert local rows (read-only from eWorks)."""
    result = QuoteAttachmentSyncResult()
    if not settings.eworks_sync_attachments_enabled:
        return result
    if not quote.eworks_quote_id:
        return result

    eworks_quote_id = quote.eworks_quote_id
    quote_ref = quote.quote_ref
    attachment_error = False
    detail_error = False

    # Prefer dedicated attachment endpoint.
    try:
        result.attachment_endpoint_called = True
        api_items = fetch_quote_attachments(eworks_quote_id)
        if api_items:
            result.endpoint_called = QUOTE_ATTACHMENT_ENDPOINT.format(id=eworks_quote_id)
            result.attachments_extracted = len(api_items)
            created, updated = sync_parent_attachment_items(
                db,
                parent_type="quote",
                parent_eworks_id=eworks_quote_id,
                parent_local_id=quote.id,
                items=api_items,
            )
            result.attachments_created = created
            result.attachments_updated = updated
            _log_quote_attachment_attempt(
                quote_ref=quote_ref,
                eworks_quote_id=eworks_quote_id,
                endpoint_called=result.endpoint_called,
                attachment_keys_found=["api_list"],
                attachments_extracted=result.attachments_extracted,
            )
            return result
    except Exception:
        attachment_error = True
        logger.exception(
            "Failed to fetch quote attachments from eWorks for quote_ref=%s eworks_quote_id=%s",
            quote_ref,
            eworks_quote_id,
        )

    if not fetch_detail_if_needed:
        result.failed = attachment_error
        _log_quote_attachment_attempt(
            quote_ref=quote_ref,
            eworks_quote_id=eworks_quote_id,
            endpoint_called=result.endpoint_called,
            attachment_keys_found=[],
            attachments_extracted=0,
        )
        return result

    # Fall back to quote detail payload embedded attachment keys.
    try:
        detail_payload, _rate_limited = fetch_quote_detail(eworks_quote_id)
        result.detail_fetched = True
        result.endpoint_called = QUOTE_DETAIL_ENDPOINT.format(id=eworks_quote_id)
        keys_found = find_attachment_like_keys(detail_payload)
        result.attachment_keys_found = keys_found
        created, updated = sync_parent_attachments_detailed(
            db,
            parent_type="quote",
            parent_eworks_id=eworks_quote_id,
            parent_local_id=quote.id,
            raw_payload=detail_payload,
        )
        result.attachments_created = created
        result.attachments_updated = updated
        result.attachments_extracted = created + updated
        _log_quote_attachment_attempt(
            quote_ref=quote_ref,
            eworks_quote_id=eworks_quote_id,
            endpoint_called=result.endpoint_called,
            attachment_keys_found=keys_found,
            attachments_extracted=result.attachments_extracted,
        )
    except Exception:
        detail_error = True
        logger.exception(
            "Failed to fetch quote detail attachments for quote_ref=%s eworks_quote_id=%s",
            quote_ref,
            eworks_quote_id,
        )

    result.failed = attachment_error and detail_error
    return result


def maybe_fetch_quote_attachments_after_list_upsert(
    db: Session,
    quote: EworksQuote,
    list_payload: dict[str, Any],
) -> QuoteAttachmentSyncResult | None:
    """During quote list sync, fetch attachments when list payload has none embedded."""
    if not settings.eworks_sync_attachments_enabled:
        return None
    if payload_has_embedded_attachments(list_payload):
        return None
    return sync_quote_attachments_from_eworks(db, quote, fetch_detail_if_needed=True)


def backfill_quote_attachments_from_eworks(
    db: Session,
    *,
    limit: int | None = None,
) -> QuoteAttachmentBackfillSummary:
    summary = QuoteAttachmentBackfillSummary()
    rows = db.query(EworksQuote).order_by(EworksQuote.synced_at.desc()).all()

    for quote in rows:
        summary.quotes_scanned += 1
        if limit is not None and summary.attachment_endpoint_calls >= limit:
            break

        try:
            result = sync_quote_attachments_from_eworks(db, quote, fetch_detail_if_needed=True)
            if result.attachment_endpoint_called:
                summary.attachment_endpoint_calls += 1
            if result.detail_fetched:
                summary.details_fetched += 1
            if result.attachments_extracted > 0:
                summary.quotes_with_attachments += 1
            summary.attachments_created += result.attachments_created
            summary.attachments_updated += result.attachments_updated
            if result.failed:
                summary.failed += 1
        except Exception:
            logger.exception(
                "Quote attachment backfill failed for quote_ref=%s eworks_quote_id=%s",
                quote.quote_ref,
                quote.eworks_quote_id,
            )
            summary.failed += 1

    db.commit()
    return summary
