from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.config import settings
from app.core.exceptions import AppError, success_response
from app.db.session import DbSession
from app.schemas.product import ProductSyncResponse
from app.services.eworks_product_sync_service import sync_products_from_eworks

router = APIRouter(prefix="/integrations/eworks", tags=["integrations"])


def _require_dashboard_password(
    x_dashboard_password: str | None = Header(default=None, alias="X-Dashboard-Password"),
) -> None:
    if not x_dashboard_password or x_dashboard_password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="Invalid dashboard password")


@router.post("/products/sync")
def sync_eworks_products(db: DbSession, _auth=Depends(_require_dashboard_password)):
    try:
        summary = sync_products_from_eworks(db)
        db.commit()
    except AppError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sync products") from exc

    return success_response(ProductSyncResponse(summary=summary))
