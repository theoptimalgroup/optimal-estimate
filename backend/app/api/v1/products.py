from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import AuthenticatedUser, require_roles
from app.core.exceptions import success_response
from app.core.security import UserRole
from app.db.session import DbSession
from app.models.product import Product
from app.schemas.product import ProductRead, ProductUpdate
from app.services.audit_helpers import record_audit, snapshot_model
from app.services.product_service import get_product, list_products, update_product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products_endpoint(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: str | None = Query(None),
    category: str | None = Query(None, description="Filter by category (eWorks trade/category)"),
    has_scope_of_work: bool | None = Query(None),
    active: bool | None = Query(None, description="Filter by active status"),
):
    products, meta = list_products(
        db,
        page=page,
        per_page=per_page,
        search=search,
        category=category,
        has_scope_of_work=has_scope_of_work,
        active=active,
    )
    return success_response([ProductRead.model_validate(p) for p in products], meta=meta)


@router.get("/{product_id}")
def get_product_endpoint(product_id: int, db: DbSession):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return success_response(ProductRead.model_validate(product))


@router.patch("/{product_id}")
def update_product_endpoint(
    product_id: int,
    body: ProductUpdate,
    db: DbSession,
    actor: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    existing = db.get(Product, product_id)
    before = snapshot_model(existing) if existing else None
    try:
        product = update_product(db, product_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    after = ProductRead.model_validate(product).model_dump(mode="json")
    record_audit(
        db,
        actor=actor,
        action="product_updated",
        entity_type="product",
        entity_id=product_id,
        before=before,
        after=after,
    )
    db.commit()
    return success_response(ProductRead.model_validate(product))
