from datetime import datetime

from pydantic import BaseModel


class EworksAcceptanceSyncRead(BaseModel):
    status: str | None = None
    synced_at: datetime | None = None
    error: str | None = None
    attempts: int = 0


class QuoteAcceptanceStatusRead(BaseModel):
    accepted: bool = False
    accepted_at: datetime | None = None
    name: str | None = None
    email: str | None = None
    notes: str | None = None
    eworks_sync: EworksAcceptanceSyncRead = EworksAcceptanceSyncRead()


class PublicQuoteAcceptanceRead(BaseModel):
    accepted: bool = False
    accepted_at: datetime | None = None
    name: str | None = None
