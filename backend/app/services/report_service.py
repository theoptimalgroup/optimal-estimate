from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.calculation_session import CalculationSession
from app.models.support import AuditLog
from app.schemas.eworks_link import Step1Snapshot
from app.schemas.report import (
    ReportClientBreakdown,
    ReportKpis,
    ReportQuoteRow,
    ReportRecentQuote,
    ReportStatusBreakdown,
    ReportSummaryRead,
    ReportTradeBreakdown,
    ReportTrendPoint,
)
from app.services.quote_acceptance_helpers import is_quote_accepted

GroupBy = Literal["day", "week", "month"]

_ZERO = Decimal("0.00")


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _extract_final_total(session: CalculationSession) -> Decimal | None:
    ui_state = session.ui_state
    if not isinstance(ui_state, dict):
        return None
    last_result = ui_state.get("last_result")
    if not isinstance(last_result, dict):
        return None
    breakdown = last_result.get("breakdown") or {}
    final_total = breakdown.get("final_total")
    if final_total is None:
        return None
    return Decimal(str(final_total))


def _has_internal_notes(session: CalculationSession) -> bool:
    ui_state = session.ui_state
    if not isinstance(ui_state, dict):
        return False
    last_result = ui_state.get("last_result")
    if not isinstance(last_result, dict):
        return False
    notes = last_result.get("internal_notes")
    if notes and str(notes).strip():
        return True
    for work in last_result.get("work_breakdowns") or []:
        if isinstance(work, dict) and work.get("internal_notes") and str(work["internal_notes"]).strip():
            return True
    return False


def _step1(session: CalculationSession) -> Step1Snapshot:
    return Step1Snapshot.model_validate(session.step1_snapshot or {})


def _period_key(dt: datetime, group_by: GroupBy) -> str:
    dt = _ensure_utc(dt)
    day = dt.date()
    if group_by == "day":
        return day.isoformat()
    if group_by == "week":
        monday = day - timedelta(days=day.weekday())
        return monday.isoformat()
    return f"{day.year}-{day.month:02d}-01"


def _apply_session_filters(
    query,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    client_id: UUID | None,
    trade_id: UUID | None,
    status: str | None,
):
    effective_status = status or "submitted"
    query = query.where(CalculationSession.status == effective_status)

    if client_id is not None:
        query = query.where(CalculationSession.client_id == client_id)
    if trade_id is not None:
        query = query.where(CalculationSession.trade_id == trade_id)

    if effective_status == "submitted":
        if date_from is not None:
            query = query.where(CalculationSession.submitted_at >= _ensure_utc(date_from))
        if date_to is not None:
            query = query.where(CalculationSession.submitted_at <= _ensure_utc(date_to))
    else:
        if date_from is not None:
            query = query.where(CalculationSession.created_at >= _ensure_utc(date_from))
        if date_to is not None:
            query = query.where(CalculationSession.created_at <= _ensure_utc(date_to))

    return query


def _count_reopened(db: Session, *, date_from: datetime | None, date_to: datetime | None) -> int:
    query = select(func.count()).select_from(AuditLog).where(AuditLog.action == "quote_reopened")
    if date_from is not None:
        query = query.where(AuditLog.created_at >= _ensure_utc(date_from))
    if date_to is not None:
        query = query.where(AuditLog.created_at <= _ensure_utc(date_to))
    return int(db.scalar(query) or 0)


def _session_rows(sessions: list[CalculationSession]) -> list[dict]:
    rows: list[dict] = []
    for session in sessions:
        step1 = _step1(session)
        total = _extract_final_total(session)
        rows.append(
            {
                "session": session,
                "step1": step1,
                "total": total,
                "has_internal_notes": _has_internal_notes(session),
            }
        )
    return rows


def get_report_summary(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    client_id: UUID | None = None,
    trade_id: UUID | None = None,
    status: str | None = None,
    group_by: GroupBy = "day",
) -> ReportSummaryRead:
    query = select(CalculationSession)
    query = _apply_session_filters(
        query,
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        trade_id=trade_id,
        status=status,
    )
    sessions = db.scalars(query).all()
    rows = _session_rows(sessions)

    totals = [row["total"] for row in rows if row["total"] is not None]
    total_value = sum(totals, _ZERO)
    submitted_count = len(rows)
    average_value = (total_value / submitted_count).quantize(Decimal("0.01")) if submitted_count else _ZERO

    with_notes = sum(1 for row in rows if row["has_internal_notes"])
    reopened_count = _count_reopened(db, date_from=date_from, date_to=date_to)
    accepted_rows = [row for row in rows if is_quote_accepted(row["session"])]
    accepted_count = len(accepted_rows)
    accepted_value = sum((row["total"] or _ZERO for row in accepted_rows), _ZERO)

    effective_status = status or "submitted"
    approved_or_ready = submitted_count if effective_status == "submitted" else None

    by_status_map: dict[str, dict[str, Decimal | int]] = defaultdict(lambda: {"count": 0, "value": _ZERO})
    by_client_map: dict[str, dict] = defaultdict(lambda: {"count": 0, "value": _ZERO, "client_id": None})
    by_trade_map: dict[str, dict] = defaultdict(lambda: {"count": 0, "value": _ZERO, "trade_id": None})
    trend_map: dict[str, dict[str, Decimal | int]] = defaultdict(lambda: {"count": 0, "value": _ZERO})

    for row in rows:
        session = row["session"]
        step1 = row["step1"]
        total = row["total"] or _ZERO
        session_status = session.status

        by_status_map[session_status]["count"] += 1
        by_status_map[session_status]["value"] += total

        if is_quote_accepted(session):
            by_status_map["accepted"]["count"] += 1
            by_status_map["accepted"]["value"] += total

        client_name = step1.client_name or "Unknown client"
        client_key = str(session.client_id) if session.client_id else client_name
        by_client_map[client_key]["count"] += 1
        by_client_map[client_key]["value"] += total
        by_client_map[client_key]["client_id"] = session.client_id
        by_client_map[client_key]["client_name"] = client_name

        trade_name = step1.trade_name or "Unknown trade"
        trade_key = str(session.trade_id) if session.trade_id else trade_name
        by_trade_map[trade_key]["count"] += 1
        by_trade_map[trade_key]["value"] += total
        by_trade_map[trade_key]["trade_id"] = session.trade_id
        by_trade_map[trade_key]["trade_name"] = trade_name

        trend_dt = session.submitted_at if effective_status == "submitted" else session.created_at
        if trend_dt is not None:
            period = _period_key(trend_dt, group_by)
            trend_map[period]["count"] += 1
            trend_map[period]["value"] += total

    by_status = [
        ReportStatusBreakdown(status=status_key, count=int(data["count"]), value=Decimal(str(data["value"])))
        for status_key, data in sorted(by_status_map.items(), key=lambda item: item[0])
    ]
    by_client = [
        ReportClientBreakdown(
            client_id=data.get("client_id"),
            client_name=data["client_name"],
            count=int(data["count"]),
            value=Decimal(str(data["value"])),
        )
        for data in sorted(by_client_map.values(), key=lambda item: (-int(item["count"]), item["client_name"]))
    ]
    by_trade = [
        ReportTradeBreakdown(
            trade_id=data.get("trade_id"),
            trade_name=data["trade_name"],
            count=int(data["count"]),
            value=Decimal(str(data["value"])),
        )
        for data in sorted(by_trade_map.values(), key=lambda item: (-int(item["count"]), item["trade_name"]))
    ]
    trend = [
        ReportTrendPoint(period=period, count=int(data["count"]), value=Decimal(str(data["value"])))
        for period, data in sorted(trend_map.items(), key=lambda item: item[0])
    ]

    recent_source = sorted(
        rows,
        key=lambda row: row["session"].submitted_at or row["session"].created_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:10]

    recent_quotes = [
        ReportRecentQuote(
            session_id=row["session"].id,
            quote_ref=row["step1"].quote_number,
            client_name=row["step1"].client_name,
            trade_name=row["step1"].trade_name,
            status=row["session"].status,
            total=row["total"],
            submitted_at=row["session"].submitted_at,
            client_accepted=is_quote_accepted(row["session"]),
            client_accepted_at=row["session"].client_accepted_at,
        )
        for row in recent_source
    ]

    return ReportSummaryRead(
        kpis=ReportKpis(
            submitted_quotes=submitted_count,
            total_value=total_value,
            average_quote_value=average_value,
            approved_or_ready_count=approved_or_ready,
            reopened_count=reopened_count,
            with_internal_notes_count=with_notes,
            accepted_count=accepted_count,
            accepted_value=accepted_value if accepted_count else _ZERO,
        ),
        by_status=by_status,
        by_client=by_client,
        by_trade=by_trade,
        trend=trend,
        recent_quotes=recent_quotes,
    )


def list_report_quotes(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    client_id: UUID | None = None,
    trade_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ReportQuoteRow], int]:
    base_query = select(CalculationSession)
    filtered = _apply_session_filters(
        base_query,
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        trade_id=trade_id,
        status=status,
    )

    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0

    effective_status = status or "submitted"
    order_column = (
        CalculationSession.submitted_at.desc()
        if effective_status == "submitted"
        else CalculationSession.created_at.desc()
    )
    sessions = db.scalars(filtered.order_by(order_column).offset(offset).limit(limit)).all()

    items = [
        ReportQuoteRow(
            session_id=row["session"].id,
            quote_ref=row["step1"].quote_number,
            job_number=row["step1"].job_number,
            client_name=row["step1"].client_name,
            trade_name=row["step1"].trade_name,
            status=row["session"].status,
            total=row["total"],
            submitted_at=row["session"].submitted_at,
            has_internal_notes=row["has_internal_notes"],
        )
        for row in _session_rows(sessions)
    ]
    return items, int(total)
