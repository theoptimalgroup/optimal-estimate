from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.calculation_session import CalculationSession
from app.models.eworks_sync import EworksJob, EworksJobAppointment, EworksQuote, EworksQuoteAppointment, EworksCustomFieldDefinition
from app.services.eworks_quote_detail_sync_service import (
    clear_quote_detail_safe_view_attempts,
    maybe_refresh_quote_detail_for_safe_view,
)
from app.services.eworks_safe_detail_service import _extract_custom_fields, build_quote_safe_detail


@pytest.fixture(autouse=True)
def _clear_safe_view_attempts():
    clear_quote_detail_safe_view_attempts()
    yield
    clear_quote_detail_safe_view_attempts()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        CalculationSession.__table__,
        EworksQuote.__table__,
        EworksCustomFieldDefinition.__table__,
        EworksJob.__table__,
        EworksJobAppointment.__table__,
        EworksQuoteAppointment.__table__,
    ):
        table.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_extract_custom_fields_from_cf_data_includes_all_keys():
    fields = _extract_custom_fields(
        {
            "cf_data": {
                "list_16": "18%",
                "txtar_45": "",
                "notes_field": "Call before visit",
            },
            "custom_field_labels": {
                "list_16": "Commission Rate",
                "txtar_45": "Acceptance Notes",
            },
        }
    )
    by_key = {field["field_key"]: field for field in fields}
    assert by_key["list_16"]["label"] == "Commission Rate"
    assert by_key["list_16"]["value"] == "18%"
    assert by_key["txtar_45"]["label"] == "Acceptance Notes"
    assert by_key["txtar_45"]["value"] == "Not available"
    assert by_key["notes_field"]["value"] == "Call before visit"


def test_extract_custom_fields_prefers_definition_label_over_field_key():
    from app.services.eworks_custom_field_definition_service import CustomFieldDefinitionView

    definitions = {
        "list_16": CustomFieldDefinitionView(
            field_key="list_16",
            label="Commission %",
            field_type="LIST",
            options=["18%"],
            sections=["QUOTE"],
        )
    }
    fields = _extract_custom_fields({"cf_data": {"list_16": "18%"}}, definitions=definitions)
    assert fields[0]["label"] == "Commission %"
    assert fields[0]["type"] == "LIST"
    assert fields[0]["options"] == ["18%"]


def test_extract_custom_fields_merges_list_and_cf_data():
    fields = _extract_custom_fields(
        {
            "custom_fields": [
                {"label": "Access Code", "field_key": "access_code", "value": "1234"},
            ],
            "cf_data": {"access_code": "5678", "list_16": "10%"},
        }
    )
    by_key = {field["field_key"]: field for field in fields}
    assert by_key["access_code"]["value"] == "5678"
    assert by_key["list_16"]["value"] == "10%"


@patch("app.core.config.settings.eworks_api_enabled", True)
@patch("app.services.eworks_quote_detail_sync_service.fetch_quote_detail")
def test_maybe_refresh_quote_detail_for_safe_view_updates_raw_payload(mock_fetch, db_session):
    clear_quote_detail_safe_view_attempts()
    quote = EworksQuote(
        eworks_quote_id=9001,
        quote_ref="Q9001",
        status="1",
        synced_at=datetime.now(timezone.utc),
    )
    db_session.add(quote)
    db_session.commit()

    mock_fetch.return_value = (
        {
            "id": 9001,
            "quote_ref": "Q9001",
            "cf_data": {
                "list_16": "18%",
                "txtar_45": "accepted",
            },
        },
        0,
    )

    refreshed = maybe_refresh_quote_detail_for_safe_view(db_session, quote, opened_directly=True)

    assert refreshed is True
    mock_fetch.assert_called_once_with(9001)
    assert isinstance(quote.raw_payload, dict)
    assert quote.raw_payload["cf_data"]["list_16"] == "18%"


@patch("app.services.eworks_quote_detail_sync_service.maybe_refresh_quote_detail_for_safe_view")
def test_build_quote_safe_detail_includes_cf_data_custom_fields(mock_refresh, db_session):
    mock_refresh.return_value = False
    quote = EworksQuote(
        eworks_quote_id=9002,
        quote_ref="Q9002",
        raw_payload={
            "cf_data": {"list_16": "18%"},
            "custom_field_labels": {"list_16": "Commission Rate"},
        },
    )
    db_session.add(quote)
    db_session.commit()

    detail = build_quote_safe_detail(db_session, quote, auto_sync_linked_jobs=False)

    assert any(field["field_key"] == "list_16" for field in detail["custom_fields"])
    assert next(field for field in detail["custom_fields"] if field["field_key"] == "list_16")[
        "label"
    ] == "Commission Rate"
