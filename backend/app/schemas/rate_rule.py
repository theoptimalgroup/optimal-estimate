from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.master_data import RateRuleRead


class RateRuleListRead(RateRuleRead):
    client_name: str | None = None
    trade_name: str | None = None


class RateRuleUsage(BaseModel):
    quotes_using_version: int = 0
    jobs_for_client: int = 0
    lookup_priority: str | None = None


class RateRuleDetailRead(RateRuleListRead):
    usage: RateRuleUsage


class RateRuleStatusUpdate(BaseModel):
    is_active: bool
