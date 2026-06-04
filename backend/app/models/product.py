from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eworks_item_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(100))
    scope_of_work: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    margin: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    tax_rate_id: Mapped[str | None] = mapped_column(String(50))
    track_stock_level: Mapped[bool] = mapped_column(Boolean, default=False)
    current_stock_level: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    category: Mapped[str | None] = mapped_column(String(255))
    category_id: Mapped[int | None] = mapped_column(Integer)
    type_: Mapped[str | None] = mapped_column("type", String(100))
    type_id: Mapped[int | None] = mapped_column(Integer)
    eworks_created_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    eworks_last_updated_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
