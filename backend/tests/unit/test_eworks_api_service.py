"""Unit tests for eWorks Customer API parsing and client."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.eworks_api import (
    EworksCustomerApiResponse,
    EworksCustomerRecord,
    build_customer_snapshot,
    client_fee_pct_from_snapshot,
    parse_commission_pct,
)
from app.services.eworks_api_service import fetch_customer_by_name

ASPIRE_API_RESPONSE = {
    "status": 1,
    "collection": {
        "meta": {"total": 1},
        "data": [
            {
                "id": 6,
                "customer_name": "Aspire",
                "full_name": "Kalam Elias",
                "cf_data": {
                    "list_16": "18%",
                    "list_8": "Some value",
                },
            }
        ],
    },
}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("18%", Decimal("0.18")),
        ("18", Decimal("0.18")),
        ("0%", Decimal("0")),
        (".00", Decimal("0")),
        ("None", Decimal("0")),
        ("not specified", Decimal("0")),
        (None, Decimal("0")),
        ("", Decimal("0")),
    ],
)
def test_parse_commission_pct(raw: str | None, expected: Decimal) -> None:
    assert parse_commission_pct(raw) == expected


def test_eworks_customer_api_response_parses_aspire_sample() -> None:
    parsed = EworksCustomerApiResponse.model_validate(ASPIRE_API_RESPONSE)
    assert parsed.status == 1
    assert parsed.collection.meta.total == 1
    assert parsed.collection.data[0].customer_name == "Aspire"
    assert parsed.collection.data[0].cf_data["list_16"] == "18%"


def test_build_customer_snapshot_from_aspire_record() -> None:
    record = EworksCustomerRecord.model_validate(ASPIRE_API_RESPONSE["collection"]["data"][0])
    snapshot = build_customer_snapshot(record)
    assert snapshot.eworks_customer_id == 6
    assert snapshot.customer_name == "Aspire"
    assert snapshot.client_fee_pct == Decimal("0.18")
    assert snapshot.commission_raw == "18%"
    assert snapshot.commission_source == "cf_data.list_16"


def test_client_fee_pct_from_snapshot() -> None:
    snapshot = build_customer_snapshot(
        EworksCustomerRecord(id=1, customer_name="Test", cf_data={"list_16": "10%"})
    )
    stored = snapshot.model_dump_for_session()
    assert client_fee_pct_from_snapshot(stored) == Decimal("0.10")
    assert client_fee_pct_from_snapshot(None) is None


def test_fetch_customer_by_name_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "eworks_api_enabled", True)
    monkeypatch.setattr(settings, "eworks_base_url", "https://eworks.test")
    monkeypatch.setattr(settings, "eworks_api_key", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ASPIRE_API_RESPONSE

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    monkeypatch.setattr("app.services.eworks_api_service.httpx.Client", lambda **kwargs: mock_client)

    snapshot = fetch_customer_by_name("Aspire")
    assert snapshot.customer_name == "Aspire"
    assert snapshot.client_fee_pct == Decimal("0.18")
    mock_client.get.assert_called_once()
    call_kwargs = mock_client.get.call_args.kwargs
    assert call_kwargs["params"] == {"customer_name": "Aspire"}
    assert call_kwargs["headers"]["api_key"] == "test-key"


def test_fetch_customer_by_name_empty_collection_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "eworks_api_enabled", True)
    monkeypatch.setattr(settings, "eworks_base_url", "https://eworks.test")
    monkeypatch.setattr(settings, "eworks_api_key", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": 1, "collection": {"meta": {"total": 0}, "data": []}}

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    monkeypatch.setattr("app.services.eworks_api_service.httpx.Client", lambda **kwargs: mock_client)

    with pytest.raises(AppError) as exc_info:
        fetch_customer_by_name("Missing Client")
    assert exc_info.value.code == "EWORKS_CUSTOMER_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_fetch_customer_by_name_http_500_raises_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "eworks_api_enabled", True)
    monkeypatch.setattr(settings, "eworks_base_url", "https://eworks.test")
    monkeypatch.setattr(settings, "eworks_api_key", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 503

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    monkeypatch.setattr("app.services.eworks_api_service.httpx.Client", lambda **kwargs: mock_client)

    with pytest.raises(AppError) as exc_info:
        fetch_customer_by_name("Aspire")
    assert exc_info.value.code == "EWORKS_API_UNAVAILABLE"
    assert exc_info.value.status_code == 502
