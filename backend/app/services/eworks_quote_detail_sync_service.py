"""Refresh and reconcile eWorks quote detail payloads for dashboard candidates."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.eworks_sync import EworksQuote
from app.services.eworks_quotes_jobs_api_service import fetch_quote_detail
from app.services.eworks_sync_service import _extract_quote_fields, enrich_customer_name_on_fields

logger = logging.getLogger(__name__)

_DASHBOARD_FETCH_LIMIT = 2000
QUOTE_DETAIL_SAFE_VIEW_RETRY_WINDOW_SECONDS = 15 * 60

_quote_detail_safe_view_attempts: dict[int, datetime] = {}


def clear_quote_detail_safe_view_attempts() -> None:
    """Clear in-memory safe-view refresh attempt timestamps (for tests)."""
    _quote_detail_safe_view_attempts.clear()


def _record_quote_detail_safe_view_attempt(eworks_quote_id: int) -> None:
    _quote_detail_safe_view_attempts[eworks_quote_id] = datetime.now(timezone.utc)


def _recent_quote_detail_safe_view_attempt(eworks_quote_id: int) -> bool:
    attempted_at = _quote_detail_safe_view_attempts.get(eworks_quote_id)
    if attempted_at is None:
        return False
    return datetime.now(timezone.utc) - attempted_at < timedelta(
        seconds=QUOTE_DETAIL_SAFE_VIEW_RETRY_WINDOW_SECONDS
    )


def should_refresh_quote_detail_for_safe_view(quote: EworksQuote) -> str | None:
    if not settings.eworks_api_enabled:
        return "eworks_api_disabled"
    if not quote.eworks_quote_id:
        return "missing_eworks_quote_id"
    if _recent_quote_detail_safe_view_attempt(quote.eworks_quote_id):
        return "recent_attempt"
    return None


def maybe_refresh_quote_detail_for_safe_view(
    db: Session,
    quote: EworksQuote,
    *,
    opened_directly: bool = True,
) -> bool:
    """Fetch full eWorks quote detail (incl. cf_data) when opening the safe detail modal."""
    if not opened_directly:
        return False

    skip_reason = should_refresh_quote_detail_for_safe_view(quote)
    if skip_reason:
        logger.info(
            "Quote detail safe-view refresh skipped quote_ref=%s eworks_quote_id=%s reason=%s",
            quote.quote_ref or "—",
            quote.eworks_quote_id if quote.eworks_quote_id is not None else "—",
            skip_reason,
        )
        return False

    assert quote.eworks_quote_id is not None
    _record_quote_detail_safe_view_attempt(quote.eworks_quote_id)

    payload, _rate_limited, failed = _fetch_detail_safe(quote.eworks_quote_id)
    if failed or payload is None:
        logger.warning(
            "Quote detail safe-view refresh failed quote_ref=%s eworks_quote_id=%s",
            quote.quote_ref or "—",
            quote.eworks_quote_id,
        )
        return False

    apply_quote_detail_from_eworks(db, quote, payload)
    db.commit()
    db.refresh(quote)
    logger.info(
        "Quote detail safe-view refresh applied quote_ref=%s eworks_quote_id=%s",
        quote.quote_ref or "—",
        quote.eworks_quote_id,
    )
    return True


@dataclass
class DashboardQuoteRefreshSummary:
    quotes_scanned: int = 0
    quotes_selected: int = 0
    details_fetched: int = 0
    quotes_updated: int = 0
    failed: int = 0
    skipped: int = 0
    rate_limited_count: int = 0
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"


@dataclass
class QuoteDetailReconcileSummary:
    quotes_scanned: int = 0
    details_fetched: int = 0
    quotes_updated: int = 0
    failed: int = 0
    skipped: int = 0
    rate_limited_count: int = 0
    elapsed_seconds: float = 0.0
    stopped_reason: str = "completed"


def apply_quote_detail_from_eworks(
    db: Session,
    quote: EworksQuote,
    detail_payload: dict[str, Any],
    *,
    synced_at: datetime | None = None,
) -> None:
    """Apply a fetched eWorks quote detail payload onto a local quote row."""
    synced = synced_at or datetime.now(timezone.utc)
    fields = _extract_quote_fields(detail_payload)
    enrich_customer_name_on_fields(db, fields)
    fields["synced_at"] = synced
    for key, value in fields.items():
        if key == "eworks_quote_id":
            continue
        setattr(quote, key, value)
    db.flush()


def select_dashboard_candidate_quotes(db: Session, *, limit: int) -> list[EworksQuote]:
    """Return draft quotes that appear in manager/admin dashboard buckets."""
    from app.services.manager_dashboard_service import classify_eworks_quote_bucket_with_reason
    from app.services.quote_search_service import quote_is_draft

    rows = (
        db.query(EworksQuote)
        .order_by(EworksQuote.quote_date.desc(), EworksQuote.synced_at.desc())
        .limit(_DASHBOARD_FETCH_LIMIT)
        .all()
    )
    candidates: list[EworksQuote] = []
    for row in rows:
        if not quote_is_draft(row):
            continue
        bucket, _ = classify_eworks_quote_bucket_with_reason(row)
        if bucket is None:
            continue
        candidates.append(row)
        if len(candidates) >= max(1, limit):
            break
    return candidates


def select_reconcile_quotes(db: Session, *, limit: int) -> list[EworksQuote]:
    """Return locally synced quotes in the configured lookback window (oldest first)."""
    lookback_days = max(1, int(settings.eworks_sync_lookback_days))
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    return (
        db.query(EworksQuote)
        .filter(EworksQuote.synced_at >= cutoff)
        .order_by(EworksQuote.synced_at.asc(), EworksQuote.id.asc())
        .limit(max(1, limit))
        .all()
    )


def _fetch_detail_safe(eworks_quote_id: int) -> tuple[dict[str, Any] | None, int, bool]:
    try:
        payload, rate_limited = fetch_quote_detail(eworks_quote_id)
        return payload, rate_limited, False
    except AppError as exc:
        if exc.code == "EWORKS_RATE_LIMITED":
            raise
        logger.exception("Failed to fetch quote detail for eworks_quote_id=%s", eworks_quote_id)
        return None, 0, True
    except Exception:
        logger.exception("Failed to fetch quote detail for eworks_quote_id=%s", eworks_quote_id)
        return None, 0, True


def refresh_dashboard_quote_details(
    db: Session,
    *,
    limit: int | None = None,
    timeout_seconds: float | None = None,
) -> DashboardQuoteRefreshSummary:
    """Fetch eWorks quote details for dashboard candidate quotes and upsert locally."""
    started = time.monotonic()
    summary = DashboardQuoteRefreshSummary()
    batch_limit = max(1, limit or settings.eworks_dashboard_quote_refresh_limit)
    timeout = float(
        timeout_seconds if timeout_seconds is not None else settings.eworks_dashboard_quote_refresh_timeout_seconds
    )

    if not settings.eworks_api_enabled:
        summary.stopped_reason = "eworks_api_disabled"
        summary.elapsed_seconds = round(time.monotonic() - started, 2)
        return summary

    candidates = select_dashboard_candidate_quotes(db, limit=batch_limit)
    summary.quotes_selected = len(candidates)
    synced_at = datetime.now(timezone.utc)

    for quote in candidates:
        if time.monotonic() - started >= timeout:
            summary.stopped_reason = "timeout"
            break

        summary.quotes_scanned += 1
        if not quote.eworks_quote_id:
            summary.skipped += 1
            continue

        try:
            payload, rate_limited, failed = _fetch_detail_safe(quote.eworks_quote_id)
            summary.rate_limited_count += rate_limited
            if failed or payload is None:
                summary.failed += 1
                continue
            apply_quote_detail_from_eworks(db, quote, payload, synced_at=synced_at)
            summary.details_fetched += 1
            summary.quotes_updated += 1
        except AppError as exc:
            if exc.code == "EWORKS_RATE_LIMITED":
                summary.rate_limited_count += 1
                summary.stopped_reason = "rate_limited"
                break
            summary.failed += 1
        except Exception:
            logger.exception(
                "Dashboard quote refresh failed quote_ref=%s eworks_quote_id=%s",
                quote.quote_ref or "—",
                quote.eworks_quote_id,
            )
            summary.failed += 1

    db.commit()
    summary.elapsed_seconds = round(time.monotonic() - started, 2)
    logger.info(
        "Dashboard quote detail refresh finished: selected=%s fetched=%s updated=%s failed=%s "
        "rate_limited=%s stopped=%s elapsed=%ss",
        summary.quotes_selected,
        summary.details_fetched,
        summary.quotes_updated,
        summary.failed,
        summary.rate_limited_count,
        summary.stopped_reason,
        summary.elapsed_seconds,
    )
    return summary


def reconcile_quote_details(
    db: Session,
    *,
    limit: int | None = None,
    timeout_seconds: float | None = None,
) -> QuoteDetailReconcileSummary:
    """Reconcile quote detail payloads for quotes in the configured lookback window."""
    started = time.monotonic()
    summary = QuoteDetailReconcileSummary()
    batch_limit = max(1, limit or settings.eworks_quote_detail_reconcile_limit)
    timeout = float(
        timeout_seconds if timeout_seconds is not None else settings.eworks_quote_detail_reconcile_timeout_seconds
    )

    if not settings.eworks_api_enabled:
        summary.stopped_reason = "eworks_api_disabled"
        summary.elapsed_seconds = round(time.monotonic() - started, 2)
        return summary

    rows = select_reconcile_quotes(db, limit=batch_limit)
    synced_at = datetime.now(timezone.utc)

    for quote in rows:
        if time.monotonic() - started >= timeout:
            summary.stopped_reason = "timeout"
            break

        summary.quotes_scanned += 1
        if not quote.eworks_quote_id:
            summary.skipped += 1
            continue

        try:
            payload, rate_limited, failed = _fetch_detail_safe(quote.eworks_quote_id)
            summary.rate_limited_count += rate_limited
            if failed or payload is None:
                summary.failed += 1
                continue
            apply_quote_detail_from_eworks(db, quote, payload, synced_at=synced_at)
            summary.details_fetched += 1
            summary.quotes_updated += 1
        except AppError as exc:
            if exc.code == "EWORKS_RATE_LIMITED":
                summary.rate_limited_count += 1
                summary.stopped_reason = "rate_limited"
                break
            summary.failed += 1
        except Exception:
            logger.exception(
                "Quote detail reconcile failed quote_ref=%s eworks_quote_id=%s",
                quote.quote_ref or "—",
                quote.eworks_quote_id,
            )
            summary.failed += 1

    db.commit()
    summary.elapsed_seconds = round(time.monotonic() - started, 2)
    logger.info(
        "Quote detail reconcile finished: scanned=%s fetched=%s updated=%s failed=%s "
        "rate_limited=%s stopped=%s elapsed=%ss",
        summary.quotes_scanned,
        summary.details_fetched,
        summary.quotes_updated,
        summary.failed,
        summary.rate_limited_count,
        summary.stopped_reason,
        summary.elapsed_seconds,
    )
    return summary
