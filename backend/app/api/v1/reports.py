from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.report import ReportQuoteRow, ReportSummaryRead
from app.services.report_service import get_report_summary, list_report_quotes

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def get_reports_summary(
    db: DbSession,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    client_id: UUID | None = Query(None),
    trade_id: UUID | None = Query(None),
    status: str | None = Query(None),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    summary = get_report_summary(
        db,
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        trade_id=trade_id,
        status=status,
        group_by=group_by,  # type: ignore[arg-type]
    )
    return success_response(ReportSummaryRead.model_validate(summary))


@router.get("/quotes")
def list_reports_quotes(
    db: DbSession,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    client_id: UUID | None = Query(None),
    trade_id: UUID | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    items, total = list_report_quotes(
        db,
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        trade_id=trade_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return success_response(
        [ReportQuoteRow.model_validate(item) for item in items],
        meta={"total": total, "limit": limit, "offset": offset},
    )
