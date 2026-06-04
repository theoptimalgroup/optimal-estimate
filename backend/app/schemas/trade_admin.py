from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TradeListRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    rate_rules_count: int = 0
    products_count: int = 0
    created_at: datetime
    updated_at: datetime


class TradeDetailRead(TradeListRead):
    pass


class TradeAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None
