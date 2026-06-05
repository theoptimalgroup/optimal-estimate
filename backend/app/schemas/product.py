from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eworks_item_id: int
    product_name: str
    product_code: str | None = None
    scope_of_work: str | None = None
    cost_price: Decimal = Decimal("0")
    selling_price: Decimal = Decimal("0")
    margin: Decimal = Decimal("0")
    tax_rate_id: str | None = None
    track_stock_level: bool = False
    current_stock_level: Decimal = Decimal("0")
    category: str | None = None
    category_id: int | None = None
    type: str | None = Field(default=None, validation_alias="type_", serialization_alias="type")
    type_id: int | None = None
    eworks_created_on: datetime | None = None
    eworks_last_updated_on: datetime | None = None
    description: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductUpdate(BaseModel):
    product_name: str | None = None
    product_code: str | None = None
    category: str | None = None
    scope_of_work: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ProductSyncItemError(BaseModel):
    eworks_item_id: str
    item_name: str
    error: str


class ProductSyncSummary(BaseModel):
    fetched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[ProductSyncItemError] = Field(default_factory=list)

    @computed_field
    @property
    def total_fetched(self) -> int:
        return self.fetched

    @computed_field
    @property
    def inserted(self) -> int:
        return self.created


class ProductSyncResponse(BaseModel):
    message: str = "eWorks products synced successfully"
    summary: ProductSyncSummary
