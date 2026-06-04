from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientListRead(BaseModel):
    id: UUID
    name: str
    billing_email: EmailStr | None
    default_vat_rate: Decimal
    is_active: bool
    aliases: list[str] = Field(default_factory=list)
    rate_rules_count: int = 0
    calculation_sessions_count: int = 0
    created_at: datetime
    updated_at: datetime


class ClientDetailRead(ClientListRead):
    pass


class ClientAdminUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    billing_email: EmailStr | None = None
    default_vat_rate: Decimal | None = None
    is_active: bool | None = None
