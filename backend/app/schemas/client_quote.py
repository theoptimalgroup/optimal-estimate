from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.quote_acceptance import PublicQuoteAcceptanceRead


class PublicQuoteWorkRead(BaseModel):
    title: str
    product_name: str | None = None
    scope: str | None = None
    description: str | None = None
    materials_summary: str | None = None
    attachments: list[dict] = Field(default_factory=list)


class PublicQuoteSummaryRead(BaseModel):
    work_charges: Decimal
    materials: Decimal
    additional_charges: Decimal
    subtotal: Decimal
    vat: Decimal
    total: Decimal


class PublicClientQuoteRead(BaseModel):
    quote_ref: str
    client_name: str
    trade_name: str
    status: str
    scope_of_work: str | None = None
    works: list[PublicQuoteWorkRead] = Field(default_factory=list)
    summary: PublicQuoteSummaryRead
    terms: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None
    acceptance: PublicQuoteAcceptanceRead = Field(default_factory=PublicQuoteAcceptanceRead)


class ClientQuoteAcceptRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    notes: str | None = Field(default=None, max_length=2000)


class ClientQuoteAcceptResponse(BaseModel):
    accepted: bool
    already_accepted: bool
    accepted_at: datetime
    quote_ref: str


class EworksAcceptanceSyncResponse(BaseModel):
    status: str | None = None
    synced_at: datetime | None = None
    error: str | None = None
    attempts: int = 0


class PublicQuoteLinkRead(BaseModel):
    public_url: str
    public_token: str
    expires_at: datetime | None = None
