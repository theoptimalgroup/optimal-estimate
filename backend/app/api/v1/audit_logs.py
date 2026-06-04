from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.audit_log import AuditLogDetailRead, AuditLogListRead
from app.services.audit_log_service import get_audit_log, list_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def list_audit_logs_endpoint(
    db: DbSession,
    search: str | None = Query(None),
    actor_email: str | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    logs, total = list_audit_logs(
        db,
        search=search,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return success_response(
        [AuditLogListRead.model_validate(item) for item in logs],
        meta={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/{audit_log_id}")
def get_audit_log_endpoint(
    audit_log_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    log = get_audit_log(db, audit_log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return success_response(AuditLogDetailRead.model_validate(log))
