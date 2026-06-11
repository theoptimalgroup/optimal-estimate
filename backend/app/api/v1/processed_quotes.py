from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.schemas.processed_dashboard import SalesPipelinePatch, SalesPipelineRead
from app.services.processed_dashboard_service import patch_sales_pipeline, pipeline_row_to_read

router = APIRouter(prefix="/processed-quotes", tags=["processed-quotes"])


@router.patch("/{quote_id}/sales-pipeline")
def patch_quote_sales_pipeline(
    quote_id: int,
    body: SalesPipelinePatch,
    db: DbSession,
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
):
    """Update local sales pipeline fields for a processed quote (never writes to eWorks)."""
    try:
        row = patch_sales_pipeline(db, quote_id, body, user)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return success_response(SalesPipelineRead.model_validate(pipeline_row_to_read(row)).model_dump())
