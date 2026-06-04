from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.client_quote import (
    ClientQuoteAcceptRequest,
    ClientQuoteAcceptResponse,
    EworksAcceptanceSyncResponse,
    PublicClientQuoteRead,
    PublicQuoteLinkRead,
)
from app.services.audit_helpers import record_audit
from app.services.client_quote_service import (
    accept_public_client_quote,
    create_or_get_public_link,
    get_public_client_quote,
    render_public_client_quote_pdf,
    revoke_public_link,
)
from app.services.eworks_acceptance_sync_service import retry_quote_acceptance_eworks_sync, sync_quote_acceptance_to_eworks
from app.services.quote_acceptance_helpers import eworks_sync_from_session
from app.schemas.eworks_link import Step1Snapshot

router = APIRouter(prefix="/client-quotes", tags=["client-quotes"])


def _handle_app_error(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/public/{public_token}")
def get_public_quote(public_token: str, db: DbSession):
    try:
        quote = get_public_client_quote(db, public_token)
    except AppError as exc:
        raise _handle_app_error(exc) from exc
    return success_response(PublicClientQuoteRead.model_validate(quote))


@router.get("/public/{public_token}/pdf")
def download_public_quote_pdf(public_token: str, db: DbSession):
    try:
        content, file_name, media_type = render_public_client_quote_pdf(db, public_token)
    except AppError as exc:
        raise _handle_app_error(exc) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/public/{public_token}/accept")
def accept_public_quote(
    public_token: str,
    body: ClientQuoteAcceptRequest,
    request: Request,
    db: DbSession,
):
    try:
        result, session, newly_accepted = accept_public_client_quote(
            db,
            public_token,
            body,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AppError as exc:
        raise _handle_app_error(exc) from exc

    if newly_accepted:
        step1 = Step1Snapshot.model_validate(session.step1_snapshot)
        record_audit(
            db,
            actor=None,
            action="client_quote_accepted",
            entity_type="calculation_session",
            entity_id=session.id,
            metadata={
                "quote_ref": step1.quote_number,
                "client_acceptance_email": session.client_acceptance_email,
                "public_link": True,
            },
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
        sync_quote_acceptance_to_eworks(db, session)
    return success_response(ClientQuoteAcceptResponse.model_validate(result))


@router.post("/{session_id}/sync-acceptance-eworks")
def sync_acceptance_to_eworks(
    session_id: UUID,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    try:
        session = retry_quote_acceptance_eworks_sync(db, session_id, actor=actor)
    except AppError as exc:
        raise _handle_app_error(exc) from exc

    sync = eworks_sync_from_session(session)
    return success_response(EworksAcceptanceSyncResponse.model_validate(sync.model_dump()))


@router.post("/{session_id}/public-link")
def create_public_quote_link(
    session_id: UUID,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER, UserRole.ESTIMATOR)),
):
    try:
        link = create_or_get_public_link(db, session_id)
    except AppError as exc:
        raise _handle_app_error(exc) from exc

    record_audit(
        db,
        actor=actor,
        action="public_quote_link_created",
        entity_type="calculation_session",
        entity_id=session_id,
        after={"public_url": link.public_url, "expires_at": link.expires_at.isoformat() if link.expires_at else None},
    )
    db.commit()
    return success_response(PublicQuoteLinkRead.model_validate(link))


@router.post("/{session_id}/revoke-public-link")
def revoke_public_quote_link(
    session_id: UUID,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    try:
        revoke_public_link(db, session_id)
    except AppError as exc:
        raise _handle_app_error(exc) from exc

    record_audit(
        db,
        actor=actor,
        action="public_quote_link_revoked",
        entity_type="calculation_session",
        entity_id=session_id,
    )
    db.commit()
    return success_response({"revoked": True})
