from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product


def list_products(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 25,
    search: str | None = None,
    category: str | None = None,
    has_scope_of_work: bool | None = None,
    active: bool | None = None,
) -> tuple[list[Product], dict]:
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)

    query = select(Product)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Product.product_name.ilike(term),
                Product.product_code.ilike(term),
                Product.scope_of_work.ilike(term),
            )
        )

    if category and category.strip():
        query = query.where(Product.category.ilike(f"%{category.strip()}%"))

    if active is not None:
        query = query.where(Product.is_active.is_(active))

    if has_scope_of_work is True:
        query = query.where(
            Product.scope_of_work.isnot(None),
            func.trim(Product.scope_of_work) != "",
        )
    elif has_scope_of_work is False:
        query = query.where(
            or_(Product.scope_of_work.is_(None), func.trim(Product.scope_of_work) == "")
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    last_page = max((total + per_page - 1) // per_page, 1) if total else 1

    products = db.scalars(
        query.order_by(Product.product_name, Product.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    meta = {
        "total": total,
        "page": page,
        "per_page": per_page,
        "last_page": last_page,
    }
    return list(products), meta


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def update_product(db: Session, product_id: int, payload: dict) -> Product | None:
    product = db.get(Product, product_id)
    if product is None:
        return None

    if "product_name" in payload and payload["product_name"] is not None:
        name = payload["product_name"].strip()
        if not name:
            raise ValueError("Product name is required")
        product.product_name = name

    if "product_code" in payload:
        product.product_code = payload["product_code"].strip() if payload["product_code"] else None

    if "category" in payload:
        product.category = payload["category"].strip() if payload["category"] else None

    if "scope_of_work" in payload:
        product.scope_of_work = payload["scope_of_work"]

    if "description" in payload:
        product.description = payload["description"]

    if "is_active" in payload and payload["is_active"] is not None:
        product.is_active = payload["is_active"]

    db.flush()
    return product
