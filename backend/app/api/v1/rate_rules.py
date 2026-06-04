from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.models.rate_rule import RateRule
from app.schemas.rate_rule import RateRuleStatusUpdate
from app.services.audit_helpers import record_audit, snapshot_model
from app.services.rate_rule_service import get_rate_rule_detail, list_rate_rules, update_rate_rule_status

router = APIRouter(prefix="/rate-rules", tags=["rate-rules"])


@router.get("")
def list_rate_rules_endpoint(
    db: DbSession,
    client_id: UUID | None = None,
    trade_id: UUID | None = None,
    client_name: str | None = Query(None, description="Search by client or XLSX client name"),
    trade_name: str | None = Query(None, description="Search by trade or XLSX trade name"),
    active: bool | None = None,
    formula_source: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    rules, total = list_rate_rules(
        db,
        client_id=client_id,
        trade_id=trade_id,
        client_name=client_name,
        trade_name=trade_name,
        active=active,
        formula_source=formula_source,
        limit=limit,
        offset=offset,
    )
    return success_response(rules, meta={"limit": limit, "offset": offset, "total": total})


@router.get("/{rule_id}")
def get_rate_rule_endpoint(
    rule_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    rule = get_rate_rule_detail(db, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rate rule not found")
    return success_response(rule)


@router.patch("/{rule_id}/status")
def update_rate_rule_status_endpoint(
    rule_id: UUID,
    body: RateRuleStatusUpdate,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.get(RateRule, rule_id)
    before = {"is_active": existing.is_active} if existing else None
    rule = update_rate_rule_status(db, rule_id, body.is_active)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rate rule not found")
    record_audit(
        db,
        actor=actor,
        action="rate_rule_status_updated",
        entity_type="rate_rule",
        entity_id=rule_id,
        before=before,
        after={"is_active": rule.is_active},
    )
    db.commit()
    return success_response(rule)
