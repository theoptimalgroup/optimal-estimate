from typing import Annotated

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import ProductSyncAccess, require_product_sync_access
from app.core.exceptions import AppError, success_response
from app.db.session import DbSession
from app.schemas.product import ProductSyncResponse
from app.services.audit_helpers import record_audit
from app.services.eworks_product_sync_service import sync_products_from_eworks

router = APIRouter(prefix="/integrations/eworks", tags=["integrations"])
logger = logging.getLogger(__name__)


def _record_product_sync_audit(db: DbSession, access: ProductSyncAccess, summary) -> None:
    metadata = {
        "fetched": summary.fetched,
        "created": summary.created,
        "updated": summary.updated,
        "failed": summary.failed,
    }
    if access.method == "password":
        metadata["auth_method"] = "dashboard_password"
        record_audit(
            db,
            actor=None,
            action="eworks_products_sync_completed",
            entity_type="product",
            entity_id=None,
            metadata={**metadata, "actor_email": "dashboard-password"},
        )
        return

    record_audit(
        db,
        actor=access.user,
        action="eworks_products_sync_completed",
        entity_type="product",
        entity_id=None,
        metadata=metadata,
    )


@router.post("/products/sync")
def sync_eworks_products(
    db: DbSession,
    access: Annotated[ProductSyncAccess, Depends(require_product_sync_access)],
):
    try:
        summary = sync_products_from_eworks(db)
        _record_product_sync_audit(db, access, summary)
        db.commit()
    except AppError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("eWorks product sync failed before completion")
        raise HTTPException(status_code=500, detail="Failed to sync products") from exc

    return success_response(ProductSyncResponse(summary=summary))
