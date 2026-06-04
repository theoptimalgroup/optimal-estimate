from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.client_admin import ClientAdminUpdate
from app.services.audit_helpers import record_audit
from app.services.client_admin_service import get_client_admin, list_clients_admin, update_client_admin

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("")
def list_clients_endpoint(
    db: DbSession,
    search: str | None = Query(None),
    active: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    clients, total = list_clients_admin(db, search=search, active=active, limit=limit, offset=offset)
    return success_response(clients, meta={"total": total, "limit": limit, "offset": offset})


@router.get("/{client_id}")
def get_client_endpoint(
    client_id: UUID,
    db: DbSession,
    _user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    client = get_client_admin(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return success_response(client)


@router.patch("/{client_id}")
def update_client_endpoint(
    client_id: UUID,
    body: ClientAdminUpdate,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    before_client = get_client_admin(db, client_id)
    before = before_client.model_dump(mode="json") if before_client else None

    try:
        client = update_client_admin(db, client_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    record_audit(
        db,
        actor=actor,
        action="client_updated",
        entity_type="client",
        entity_id=client_id,
        before=before,
        after=client.model_dump(mode="json"),
    )
    db.commit()
    return success_response(client)
