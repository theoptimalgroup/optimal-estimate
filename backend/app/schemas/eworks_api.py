from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class EworksCustomerSnapshot(BaseModel):
    eworks_customer_id: int
    customer_name: str
    client_fee_pct: Decimal
    commission_source: str = "cf_data.list_16"
    commission_raw: str | None = None
    fetched_at: datetime
    raw: dict[str, Any] = Field(default_factory=dict)

    def model_dump_for_session(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        return data


class EworksCustomerRecord(BaseModel):
    id: int
    customer_name: str
    cf_data: dict[str, Any] = Field(default_factory=dict)


class EworksCustomerCollectionMeta(BaseModel):
    total: int = 0


class EworksCustomerCollection(BaseModel):
    meta: EworksCustomerCollectionMeta = Field(default_factory=EworksCustomerCollectionMeta)
    data: list[EworksCustomerRecord] = Field(default_factory=list)


class EworksCustomerApiResponse(BaseModel):
    status: int
    collection: EworksCustomerCollection = Field(default_factory=EworksCustomerCollection)


def parse_commission_pct(raw_value: str | None) -> Decimal:
    if raw_value is None:
        return Decimal("0")
    normalized = str(raw_value).strip()
    if not normalized:
        return Decimal("0")
    lowered = normalized.lower()
    if lowered in {"none", "not specified", "n/a", "na"}:
        return Decimal("0")
    cleaned = normalized.rstrip("%").strip()
    if not cleaned or cleaned in {".00", "0", "0.0", "0.00"}:
        return Decimal("0")
    try:
        pct = Decimal(cleaned)
    except Exception:
        return Decimal("0")
    if pct < 0:
        return Decimal("0")
    return pct / Decimal("100")


def build_customer_snapshot(record: EworksCustomerRecord) -> EworksCustomerSnapshot:
    commission_raw = record.cf_data.get("list_16")
    commission_raw_str = str(commission_raw) if commission_raw is not None else None
    return EworksCustomerSnapshot(
        eworks_customer_id=record.id,
        customer_name=record.customer_name,
        client_fee_pct=parse_commission_pct(commission_raw_str),
        commission_raw=commission_raw_str,
        fetched_at=datetime.now(timezone.utc),
        raw=record.model_dump(mode="json"),
    )


def client_fee_pct_from_snapshot(snapshot: dict | None) -> Decimal | None:
    if not snapshot:
        return None
    value = snapshot.get("client_fee_pct")
    if value is None:
        return None
    return Decimal(str(value))
