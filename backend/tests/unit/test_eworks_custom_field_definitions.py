"""Tests for eWorks custom field definition sync and label mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.eworks_sync import EworksCustomFieldDefinition, EworksQuote
from app.services.eworks_custom_field_definition_service import (
    build_quote_custom_fields_debug,
    parse_custom_field_definition,
    parse_list_options,
    sync_custom_field_definitions,
)
from app.services.eworks_safe_detail_service import _extract_custom_fields


SAMPLE_DEFINITION = {
    "custom_field_id": 16,
    "field_key": "list_16",
    "field_label": "Commission %",
    "field_value": "0%\r\n5%\r\n18%",
    "default_value": "",
    "field_type": "LIST",
    "status": 1,
    "allowed_sections": {
        "section_settings": [
            {"section": "QUOTE"},
            {"section": "CUSTOMER"},
        ]
    },
}


def test_parse_custom_field_definition_extracts_list_options():
    parsed = parse_custom_field_definition(SAMPLE_DEFINITION)
    assert parsed is not None
    assert parsed["field_key"] == "list_16"
    assert parsed["field_label"] == "Commission %"
    assert parsed["field_type"] == "LIST"
    assert parsed["options"] == ["0%", "5%", "18%"]
    assert parsed["sections"] == ["QUOTE", "CUSTOMER"]


def test_parse_list_options_splits_crlf_values():
    assert parse_list_options("A\r\nB\r\nC") == ["A", "B", "C"]


def test_extract_custom_fields_uses_synced_definition_labels():
    definitions = definitions_lookup_map_from_rows(
        [
            EworksCustomFieldDefinition(
                eworks_custom_field_id=16,
                field_key="list_16",
                field_label="Commission %",
                field_type="LIST",
                options=["0%", "18%"],
                sections=["QUOTE"],
            )
        ]
    )
    fields = _extract_custom_fields(
        {"cf_data": {"list_16": "18%", "txt_9": "Kitchen refit"}},
        definitions=definitions,
    )
    by_key = {field["field_key"]: field for field in fields}
    assert by_key["list_16"]["label"] == "Commission %"
    assert by_key["list_16"]["type"] == "LIST"
    assert by_key["list_16"]["value"] == "18%"
    assert by_key["list_16"]["options"] == ["0%", "18%"]
    assert by_key["txt_9"]["label"] == "txt_9"
    assert by_key["txt_9"]["type"] == "TEXT"


def definitions_lookup_map_from_rows(rows):
    from app.services.eworks_custom_field_definition_service import CustomFieldDefinitionView

    return {
        row.field_key: CustomFieldDefinitionView(
            field_key=row.field_key,
            label=row.field_label or row.field_key,
            field_type=row.field_type,
            options=row.options if isinstance(row.options, list) else None,
            sections=row.sections if isinstance(row.sections, list) else None,
        )
        for row in rows
    }


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EworksCustomFieldDefinition.__table__.create(engine)
    EworksQuote.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@patch("app.services.eworks_custom_field_definition_service.fetch_all_custom_field_definitions")
def test_sync_custom_field_definitions_upserts_rows(mock_fetch, db_session):
    mock_fetch.return_value = [SAMPLE_DEFINITION]
    summary = sync_custom_field_definitions(db_session)
    assert summary.fetched == 1
    assert summary.created == 1
    row = db_session.query(EworksCustomFieldDefinition).filter_by(field_key="list_16").one()
    assert row.field_label == "Commission %"
    assert row.options == ["0%", "5%", "18%"]


def test_build_quote_custom_fields_debug_merges_definition_and_value(db_session):
    db_session.add(
        EworksCustomFieldDefinition(
            eworks_custom_field_id=9,
            field_key="txt_9",
            field_label="Short Quote Description",
            field_type="TEXT",
            sections=["QUOTE"],
            synced_at=datetime.now(timezone.utc),
        )
    )
    quote = EworksQuote(
        eworks_quote_id=100,
        quote_ref="Q100",
        raw_payload={"cf_data": {"txt_9": "Boiler replacement"}},
    )
    db_session.add(quote)
    db_session.commit()

    with patch(
        "app.services.eworks_custom_field_definition_service.ensure_custom_field_definitions",
        return_value=False,
    ):
        rows = build_quote_custom_fields_debug(db_session, quote)

    txt_9 = next(row for row in rows if row["field_key"] == "txt_9")
    assert txt_9["label"] == "Short Quote Description"
    assert txt_9["type"] == "TEXT"
    assert txt_9["section"] == "QUOTE"
    assert txt_9["value"] == "Boiler replacement"
